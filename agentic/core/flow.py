import ast
import inspect
import textwrap
import threading
import concurrent.futures
from collections import defaultdict

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
    # Put the stmt in its own Module wrapper so compile() accepts it
    mod = ast.Module(body=[stmt], type_ignores=[])
    return compile(mod, filename="<flow>", mode="exec")


# --------------------------------------------------------------------------- #
#  The decorator                                                              #
# --------------------------------------------------------------------------- #
def flow(fn):
    """
    Transform *fn* into a function that executes in data‑dependency order.
    * Straight‑line code only (no 'if', 'for', 'while', 'with', etc.).
    * The final 'return' may be any expression; its value is returned.
    * Truly independent statements run concurrently via a thread pool.
    """
    # 1. --- Parse the function source ---------------------------------------
    src        = textwrap.dedent(inspect.getsource(fn))
    tree       = ast.parse(src)
    fnode      = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    statements = fnode.body

    # 2. --- Build nodes & dependencies --------------------------------------
    nodes          = []                       # index -> {code, deps, dependents}
    var_producer   = {}                       # varname -> node index
    dependents_map = defaultdict(set)         # node -> children that need it
    return_expr    = None                     # AST of the return expression
    return_reads   = set()

    for idx, stmt in enumerate(statements):
        if isinstance(stmt, ast.Return):       # remember return, don't treat as node
            return_expr  = stmt.value
            return_reads, _ = _reads_writes(stmt)   # writes set is always empty
            continue

        reads, writes = _reads_writes(stmt)
        deps          = {var_producer[v] for v in reads if v in var_producer}
        code          = _compile_stmt(stmt)
        nodes.append(dict(code=code, deps=set(deps), dependents=set()))

        # map “this node” back onto variables it *produces*
        for v in writes:
            var_producer[v] = idx

    # Fill dependents sets (reverse edges)
    for child_idx, n in enumerate(nodes):
        for parent in n["deps"]:
            dependents_map[parent].add(child_idx)
    for idx, n in enumerate(nodes):
        n["dependents"] = dependents_map[idx]

    # 3. --- Pre‑compile the return expression --------------------------------
    if return_expr is None:
        # no explicit return => implicit 'None'
        return_code = None
    else:
        return_code = compile(ast.Expression(return_expr),
                              filename="<flow‑return>", mode="eval")

    # ----------------------------------------------------------------------- #
    #  The wrapped function                                                   #
    # ----------------------------------------------------------------------- #
    def wrapped(*args, **kwargs):
        # --- initialise call namespace -------------------------------------
        globals_ns   = fn.__globals__
        locals_ns    = {}
        argnames     = fn.__code__.co_varnames[:fn.__code__.co_argcount]
        locals_ns.update(dict(zip(argnames, args)))
        locals_ns.update(kwargs)

        # --- track when every node's deps are satisfied --------------------
        deps_remaining = {i: len(n["deps"]) for i, n in enumerate(nodes)}

        # Thread‑safe bookkeeping ------------------------------------------
        lock      = threading.Lock()
        futures   = {}              # future -> node index
        executor  = concurrent.futures.ThreadPoolExecutor(max_workers=len(nodes) or 1)

        def submit_node(i):
            """Submit node *i* for execution in the shared namespace."""
            fut = executor.submit(exec, nodes[i]["code"], globals_ns, locals_ns)
            futures[fut] = i

        # kick‑off nodes with zero dependencies
        for i, n in enumerate(nodes):
            if deps_remaining[i] == 0:
                submit_node(i)

        # event loop: wait for tasks, schedule children when ready
        while futures:
            done, _ = concurrent.futures.wait(
                futures, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for fut in done:
                idx = futures.pop(fut)           # which node just finished?
                if fut.exception():
                    # Propagate the very first exception out of wrapped()
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise fut.exception()

                # schedule dependents that became free
                for child in nodes[idx]["dependents"]:
                    with lock:
                        deps_remaining[child] -= 1
                        if deps_remaining[child] == 0:
                            submit_node(child)

        executor.shutdown(wait=True)

        # --- evaluate and return the function’s result ---------------------
        if return_code is None:          # no 'return' -> None
            return None
        return eval(return_code, globals_ns, locals_ns)

    wrapped.__name__        = fn.__name__
    wrapped.__doc__         = fn.__doc__
    wrapped.__qualname__    = fn.__qualname__
    wrapped.__annotations__ = fn.__annotations__
    return wrapped
