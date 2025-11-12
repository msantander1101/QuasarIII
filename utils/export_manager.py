import zipfile
import io
from datetime import datetime
from typing import List, Dict
import json
import pandas as pd


def export_batch_zip(results: List[Dict], include_pdfs: bool = False):
    """
    Exporta batch completo como ZIP con:
    - JSON raw
    - CSV por módulo
    - PDFs individuales
    - Reporte ejecutivo
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # JSON principal
        zip_file.writestr(
            "batch_results.json",
            json.dumps(results, indent=2, ensure_ascii=False)
        )

        # CSVs por módulo
        for module_name in ["socmint", "breachdata", "emailint"]:
            rows = []
            for result in results:
                module_data = result['modules'].get(module_name, {})
                if isinstance(module_data, dict) and module_data.get('profiles'):
                    for item in module_data['profiles']:
                        row = result['target'].copy()
                        row.update(item)
                        rows.append(row)

            if rows:
                df = pd.DataFrame(rows)
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                zip_file.writestr(f"{module_name}.csv", csv_buffer.getvalue())

        # Reporte ejecutivo
        executive_summary = generate_executive_summary(results)
        zip_file.writestr("executive_summary.md", executive_summary)

    return zip_buffer.getvalue()


def generate_executive_summary(results: List[Dict]) -> str:
    """Genera markdown con resumen ejecutivo"""
    total_targets = len(results)
    total_findings = sum(len(r.get('modules', {})) for r in results)

    report = f"""# Batch OSINT Report
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Targets**: {total_targets}
**Total Findings**: {total_findings}
**Success Rate**: {(sum(1 for r in results if r['status'] == 'completed') / total_targets * 100):.1f}%

## Module Breakdown
"""

    # Añadir stats por módulo
    for module_name in ["socmint", "breachdata"]:
        count = sum(len(r['modules'].get(module_name, {}).get('profiles', [])) for r in results)
        report += f"- **{module_name}**: {count} findings\n"

    return report