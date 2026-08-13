from pathlib import Path
for label, path in [
    ("source", r"d:\SourceCode\WorkforcePlanning\PLH Weekly Workforce Planning.html"),
    ("publish", r"D:\WorkforcePlanning\WorkforcePublish\wwwroot\index.html"),
]:
    b = Path(path).read_bytes()
    # find b'Ph' near title
    i = b.find(b"<title>")
    print(label, "title bytes", list(b[i:i+40]))
    # count utf-8 ú C3 BA vs latin1 FA
    print(label, "utf8 ú count", b.count(bytes([0xC3, 0xBA])))
    print(label, "latin1 ú count", b.count(bytes([0xFA])))
