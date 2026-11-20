# One-off fix: convert Postman collection URL objects to raw string URLs
# so Django's required trailing slashes are preserved. (Temporary - delete after use.)
import json

P = r"C:/Users/mycha/ARKCafe_SAD/postman/ARKCafe-E2E.postman_collection.json"
c = json.load(open(P, encoding="utf-8"))
n = 0

def walk(items):
    global n
    for i in items:
        if "item" in i:
            walk(i["item"])
        else:
            u = i["request"]["url"]
            if isinstance(u, dict) and "raw" in u:
                i["request"]["url"] = u["raw"]
                n += 1

walk(c["item"])
json.dump(c, open(P, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("fixed", n, "urls -> raw strings with trailing slashes")
