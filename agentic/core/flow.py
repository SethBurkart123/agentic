import ast
import inspect
import textwrap
import threading
import concurrent.futures
from collections import defaultdict
from functools import wraps

from rich.live import Live
from rich.table import Table
from rich.console import Console

# --------------------------------------------------------------------------- #
#  Helper utilities                                                           #
# --------------------------------------------------------------------------- #
def _reads_writes(node: ast.stmt):
    """Return (reads, writes) variable-name sets for a single AST statement."""
    reads, writes = set(), set()

    if isinstance(node, ast.FunctionDef):
        writes.add(node.name)

    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Load):
                reads.add(n.id)
            elif isinstance(n.ctx, ast.Store):
                writes.add(n.id)

    reads.difference_update(dir(__builtins__))
    return reads, writes


def _compile_stmt(stmt: ast.stmt):
    """Compile a single statement to a code object ready for exec()."""
    mod = ast.Module(body=[stmt], type_ignores=[])
    return compile(mod, filename="<flow>", mode="exec")


# --------------------------------------------------------------------------- #
#  The decorator                                                              #
# --------------------------------------------------------------------------- #
def flow(_fn=None, *, debug=False):
    def decorator(fn):
        # 1. --- Parse the function source ---------------------------------------
        src = textwrap.dedent(inspect.getsource(fn))
        tree = ast.parse(src)
        fnode = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
        statements = fnode.body

        # 2. --- Build nodes & dependencies --------------------------------------
        nodes = []
        var_producer = {}
        dependents_map = defaultdict(set)
        return_expr = None
        return_reads = set()

        for idx, stmt in enumerate(statements):
            if isinstance(stmt, ast.Return):
                return_expr = stmt.value
                return_reads, _ = _reads_writes(stmt)
                continue

            reads, writes = _reads_writes(stmt)
            deps = {var_producer[v] for v in reads if v in var_producer}
            code = _compile_stmt(stmt)
            nodes.append(dict(code=code, deps=set(deps), dependents=set()))

            for v in writes:
                var_producer[v] = idx

        for child_idx, n in enumerate(nodes):
            for parent in n["deps"]:
                dependents_map[parent].add(child_idx)
        for idx, n in enumerate(nodes):
            n["dependents"] = dependents_map[idx]

        # 3. --- Compile return expression ----------------------------------------
        if return_expr is None:
            return_code = None
        else:
            return_code = compile(ast.Expression(return_expr), filename="<flow-return>", mode="eval")

        # ----------------------------------------------------------------------- #
        #  The wrapped function                                                   #
        # ----------------------------------------------------------------------- #
        @wraps(fn)
        def wrapped(*args, **kwargs):
            globals_ns = fn.__globals__
            locals_ns = {}
            argnames = fn.__code__.co_varnames[:fn.__code__.co_argcount]
            locals_ns.update(dict(zip(argnames, args)))
            locals_ns.update(kwargs)

            deps_remaining = {i: len(n["deps"]) for i, n in enumerate(nodes)}
            lock = threading.Lock()
            futures = {}
            statuses = {i: "pending" for i in range(len(nodes))}
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(nodes) or 1)
            console = Console()

            def submit_node(i):
                statuses[i] = "running"
                fut = executor.submit(exec, nodes[i]["code"], globals_ns, locals_ns)
                futures[fut] = i

            def build_table():
                table = Table(title="Flow Debugger")
                table.add_column("Node", justify="right")
                table.add_column("Status", justify="left")
                for i, status in statuses.items():
                    table.add_row(f"{i}", status)
                return table

            live = Live(build_table(), refresh_per_second=5, console=console) if debug else None
            if live:
                live.start()

            for i, n in enumerate(nodes):
                if deps_remaining[i] == 0:
                    submit_node(i)

            while futures:
                done, _ = concurrent.futures.wait(
                    futures, return_when=concurrent.futures.FIRST_COMPLETED
                )
                for fut in done:
                    idx = futures.pop(fut)
                    exc = fut.exception()
                    if exc:
                        statuses[idx] = "error"
                        if live:
                            live.update(build_table())
                        executor.shutdown(wait=False, cancel_futures=True)
                        raise exc
                    statuses[idx] = "done"
                    for child in nodes[idx]["dependents"]:
                        with lock:
                            deps_remaining[child] -= 1
                            if deps_remaining[child] == 0:
                                submit_node(child)
                    if live:
                        live.update(build_table())

            executor.shutdown(wait=True)
            if live:
                live.stop()

            if return_code is None:
                return None
            return eval(return_code, globals_ns, locals_ns)

        return wrapped

    if callable(_fn):
        return decorator(_fn)
    else:
        return decorator
