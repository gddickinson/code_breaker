"""Scientific, columnar, spreadsheet and certificate files, through the readers adapted from textview."""
import csv
import io

ROWS = 60


def _table(text: str) -> tuple[list, list]:
    rows = list(csv.reader(io.StringIO(text)))
    return (rows[0], rows[1:ROWS + 1]) if rows else ([], [])


def columnar(path: str) -> dict:
    from .parquet_loader import file_metadata, read_as_csv

    header, rows = _table(read_as_csv(path, row_cap=ROWS))
    meta = {k: str(v)[:80] for k, v in file_metadata(path).items() if not isinstance(v, (list, dict))}
    return {"view": "table", "header": header, "rows": rows, "facts": meta}


def hierarchical(path: str) -> dict:
    from .hdf5_loader import dataset_metadata, list_datasets, load_dataset_as_csv

    names = list_datasets(path)
    out = {"view": "tables", "tables": [], "facts": {"Datasets": len(names)}}
    for name in names[:8]:
        meta = dataset_metadata(path, name)
        header, rows = _table(load_dataset_as_csv(path, name, row_cap=20))
        shape = meta.get("shape", meta.get("Shape", ""))
        out["tables"].append({"name": f"{name}  {shape}  {meta.get('dtype', meta.get('Dtype', ''))}", "rows_total": len(rows), "header": header, "rows": rows})
    return out


def spreadsheet(path: str) -> dict:
    from .spreadsheet_loader import list_sheets, load_sheet_as_csv

    sheets = list_sheets(path)
    out = {"view": "tables", "tables": [], "facts": {"Sheets": len(sheets)}}
    for sh in sheets[:5]:
        header, rows = _table(load_sheet_as_csv(path, sh))
        out["tables"].append({"name": sh, "rows_total": len(rows), "header": header, "rows": rows[:30]})
    return out


def certificate(path: str) -> dict:
    from .cert_loader import render_markdown

    return {"view": "text", "text": render_markdown(path), "facts": {}}


READERS = {"parquet": columnar, "feather": columnar, "arrow": columnar, "hdf5": hierarchical, "netcdf": hierarchical, "xlsx": spreadsheet, "ods": spreadsheet, "cert": certificate}
