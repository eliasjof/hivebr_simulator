"""web/templates (pt-BR) and web/templates/en: same logic, both run in the Python harness."""
import ast

from harness import REPO, check, env, moved, run_for

TPL = REPO / "web" / "templates"
NAMES = sorted(p.name for p in TPL.glob("*.py"))


def _strip_docstrings(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                    and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree


def _normalize_prints(tree):
    """print(...) text is translated; keep only its non-literal expressions (f-string fields)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            args = []
            for a in node.args:
                if isinstance(a, ast.Constant):
                    args.append(ast.Constant(value=""))
                elif isinstance(a, ast.JoinedStr):
                    args.append(ast.Tuple(elts=[v.value for v in a.values if isinstance(v, ast.FormattedValue)], ctx=ast.Load()))
                else:
                    args.append(a)
            node.args = args
    return tree


def logic_dump(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return ast.dump(_normalize_prints(_strip_docstrings(tree)))


def test_en_templates_exist_and_are_english():
    en = sorted(p.name for p in (TPL / "en").glob("*.py"))
    check(en == NAMES, (en, NAMES))
    for n in NAMES:
        text = (TPL / "en" / n).read_text(encoding="utf-8")
        check(not any(c in text for c in "áàâãçéêíóôõúÁÃÇÉÓ"), f"{n}: accented (Portuguese) text left in the English version")


def test_en_templates_have_identical_logic():
    for n in NAMES:
        check(logic_dump(TPL / n) == logic_dump(TPL / "en" / n), f"{n}: English version differs in logic")


def _run_template(path, frames, expect_text):
    with env() as e:
        # Exemplos com vários arquivos: as abas irmãs (módulos importados pelo
        # script principal) são gravadas ao lado do arquivo de entrada.
        for sibling in path.parent.glob("*.py"):
            if sibling.name != path.name:
                (e.root / "examples" / sibling.name).write_text(sibling.read_text(encoding="utf-8"), encoding="utf-8")
        r = run_for(e, path.read_text(encoding="utf-8"), frames)
        check(r["ok"] and r["error"] is None, (path.name, r))
        check(expect_text in e.stdout, (path.name, e.stdout[-300:]))
        check(moved(e.host) > 0.05 or path.name.startswith("seguidor"), f"{path.name}: robots did not move")


def test_templates_run_in_both_languages():
    expect = {
        "inicio_rapido.py": ("Rota com", "Route with"),
        "importando_modulo.py": ("Importado de agent_lib.py", "Imported from agent_lib.py"),
        "holonomico.py": ("Robô holonômico", "Holonomic robot"),
        "lidar_desvio.py": ("obstáculos no caminho", "obstacles on the way"),
        "seguidor_de_linha.py": ("Sensores:", "Sensors:"),
        "swarm_centralizado.py": ("Formação em", "Formation:"),
        "swarm_descentralizado.py": ("Enxame com", "Swarm with"),
        "demonstracao.py": ("Demonstração:", "Demo:"),
    }
    for n, (pt, en) in expect.items():
        _run_template(TPL / n, 80, pt)
        _run_template(TPL / "en" / n, 80, en)
