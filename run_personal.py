"""
Script maestro para la PC personal.

Uso:
    cd paradigmasportsbetting
    python run_personal.py

Hace TODO automáticamente:
1. git pull
2. Lee NOTAS_DEV.md para ver qué hay pendiente
3. Ejecuta los comandos
4. Captura output
5. Escribe resultados en RESULTADOS_TEST.md
6. git push
"""

import subprocess
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
NOTAS = ROOT / "NOTAS_DEV.md"
RESULTADOS = ROOT / "RESULTADOS_TEST.md"
PARADIGMA = ROOT / "paradigma"


def run_cmd(cmd: str, cwd: str = None, timeout: int = 600) -> tuple[int, str]:
    """Ejecuta un comando y retorna (exit_code, output)."""
    print(f"\n  ▶ {cmd}")
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd or str(ROOT),
            capture_output=True, text=True, timeout=timeout,
        )
        output = result.stdout + result.stderr
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return -1, f"TIMEOUT ({timeout}s)"
    except Exception as e:
        return -1, str(e)


def git_pull():
    """Pull latest code."""
    print("\n📥 Pulling latest code...")
    code, out = run_cmd("git pull")
    if code != 0:
        print(f"  ⚠️ git pull falló: {out}")
    else:
        print(f"  ✅ {out.strip().split(chr(10))[-1]}")


def git_push(message: str):
    """Add, commit, push results."""
    print("\n📤 Pushing results...")
    run_cmd("git add RESULTADOS_TEST.md")
    run_cmd(f'git commit -m "{message}"')
    code, out = run_cmd("git push")
    if code == 0:
        print("  ✅ Resultados pusheados")
    else:
        print(f"  ⚠️ Push: {out}")


def append_result(title: str, content: str):
    """Append a result block to RESULTADOS_TEST.md."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    block = f"\n### {ts} — {title}\n\n```\n{content[-8000:]}\n```\n\n---\n"

    # Insertar después del primer "---" (después del header)
    text = RESULTADOS.read_text(encoding="utf-8") if RESULTADOS.exists() else ""
    # Buscar la primera línea "---" después de contenido
    lines = text.split("\n")
    insert_idx = 0
    found_header = False
    for i, line in enumerate(lines):
        if line.strip() == "---" and i > 2:
            insert_idx = i + 1
            found_header = True
            break
    if not found_header:
        insert_idx = len(lines)

    lines.insert(insert_idx, block)
    RESULTADOS.write_text("\n".join(lines), encoding="utf-8")
    print(f"  📝 Resultado escrito en RESULTADOS_TEST.md")


def menu():
    """Menú interactivo."""
    print("\n" + "=" * 60)
    print("🖥️  PC PERSONAL — Menú de ejecución")
    print("=" * 60)
    print()
    print("  1. Scanner completo (1xBet)")
    print("  2. Scanner multi-book (1xBet + MelBet + 20Bet)")
    print("  3. Verificar odds (links directos)")
    print("  4. API Sniffer — bet365")
    print("  5. API Sniffer — DoradoBet")
    print("  6. API Sniffer — MelBet")
    print("  7. API Sniffer — 20Bet")
    print("  8. Correr comando personalizado")
    print("  0. Salir")
    print()

    choice = input("  Opción: ").strip()
    return choice


def run_task(task_name: str, cmd: str, timeout: int = 600):
    """Ejecuta una tarea, captura output, escribe resultados, push."""
    print(f"\n🚀 Ejecutando: {task_name}")
    print(f"   Comando: {cmd}")
    print(f"   Timeout: {timeout}s")
    print(f"   {'─'*50}")

    code, output = run_cmd(cmd, cwd=str(PARADIGMA), timeout=timeout)

    print(f"\n   {'─'*50}")
    print(f"   Exit code: {code}")
    print(f"   Output: {len(output)} chars")

    # Mostrar últimas líneas
    last_lines = output.strip().split("\n")[-30:]
    print(f"\n   Últimas 30 líneas:")
    for line in last_lines:
        print(f"   {line}")

    # Escribir resultado
    summary = f"Comando: {cmd}\nExit code: {code}\n\n{output}"
    append_result(task_name, summary)

    # Push
    git_push(f"test: {task_name}")

    return code, output


def main():
    os.chdir(str(ROOT))
    git_pull()

    while True:
        choice = menu()

        if choice == "0":
            print("\n👋 Bye!")
            break
        elif choice == "1":
            run_task(
                "Scanner v2 — 1xBet",
                "python -m scraping.scanner_v2",
                timeout=600,
            )
        elif choice == "2":
            run_task(
                "Scanner v2 — Multi-book (1xBet+MelBet+20Bet)",
                "python -m scraping.scanner_v2 --books 1xbet,melbet,20bet",
                timeout=1200,
            )
        elif choice == "3":
            run_task(
                "Verify odds",
                "python -m scraping.verify_odds",
                timeout=600,
            )
        elif choice == "4":
            run_task(
                "API Sniffer — bet365",
                "python -m scraping.api_sniffer bet365",
                timeout=120,
            )
        elif choice == "5":
            run_task(
                "API Sniffer — DoradoBet",
                "python -m scraping.api_sniffer doradobet",
                timeout=120,
            )
        elif choice == "6":
            run_task(
                "API Sniffer — MelBet",
                "python -m scraping.api_sniffer melbet",
                timeout=120,
            )
        elif choice == "7":
            run_task(
                "API Sniffer — 20Bet",
                "python -m scraping.api_sniffer 20bet",
                timeout=120,
            )
        elif choice == "8":
            cmd = input("  Comando (desde carpeta paradigma): ").strip()
            if cmd:
                run_task(f"Custom: {cmd[:50]}", cmd, timeout=600)
        else:
            print("  Opción no válida")

        print("\n" + "=" * 60)
        input("  Presione ENTER para continuar...")


if __name__ == "__main__":
    main()
