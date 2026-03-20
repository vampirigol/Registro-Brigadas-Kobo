#!/usr/bin/env python3
"""
Prueba de llenado automático con excel_de_prueba.xlsx.

1. Asegúrate de tener la app corriendo (./run.sh) y abierta en localhost:5001.
2. Sube excel_de_prueba.xlsx en la app.
3. O bien ejecuta este script para una prueba directa:

    python run_llenado_prueba.py

   Esto cargará el Excel, aplicará reglas y llenará 1 registro en el formulario.
   La ventana del navegador se abrirá automáticamente.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def main():
    excel_path = PROJECT_ROOT / "excel_de_prueba.xlsx"
    if not excel_path.exists():
        print("Ejecuta primero: python create_excel_prueba.py")
        return 1

    from excel_loader import load_excel_to_records
    from filling_rules import apply_rules
    from runner import run_carga

    records = load_excel_to_records(excel_path)
    if not records:
        print("No se cargaron registros del Excel")
        return 1

    print(f"Registros cargados: {len(records)}")
    record = apply_rules(records[0])
    print(f"Campos a llenar: {len(record)}")
    for k, v in sorted(record.items()):
        print(f"  {k}: {repr(v)[:50]}")

    print("\nIniciando llenado en el formulario (se abrirá ventana del navegador)...")
    # Usar runner para una fila
    run_carga(
        excel_path=excel_path,
        progress_callback=lambda evt: print(f"  [evento] {evt.get('event', '?')}: {evt.get('message', '')}"),
        headless=False,
        wait_for_user_confirm=False,
        row_indices=[0],
        defaults={"Estado_brigada": "Baja California Sur", "Lugar": "Santa Rosalía"},
    )
    print("Listo. Revisa el formulario en la ventana.")
    return 0


if __name__ == "__main__":
    exit(main())
