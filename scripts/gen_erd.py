"""Generate Mermaid (.mmd) and draw.io (.drawio) ERDs from the modeling docs.

Usage (저장소 루트에서): python3 scripts/gen_erd.py modeling
Reads table definitions from 01_고객.md ~ 06_클레임.md and writes into <modeling_dir>/erd/.
"""
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

MODELING = Path(sys.argv[1])
OUT = MODELING / "erd"

DOCS = [("customer", "01_고객.md"), ("category", "02_카테고리.md"), ("product", "03_상품.md"), ("order", "04_주문.md"), ("payment", "05_결제_배송.md"), ("claim", "06_클레임.md")]

# ---------- parse table definitions ----------
HEAD = re.compile(r"^#### [①-⑳]\s*(.+?)\s*`([a-z_]+)`")


def domain_token(d):
    if d.startswith("번호"):
        return "NUM"
    if d.startswith("명"):
        return "NAME"
    if d.startswith("코드"):
        return "CODE"
    if d.startswith("여부"):
        return "YN"
    if d.startswith("일시"):
        return "DT"
    if d.startswith("일자"):
        return "DATE"
    if d.startswith("금액"):
        return "AMT"
    if d.startswith("숫자"):
        return "DEC" if "," in d else "INT"
    if d.startswith("해시"):
        return "HASH"
    if d.startswith("암호문"):
        return "ENC"
    if d.startswith("UUID"):
        return "UUID"
    if d.startswith("대용량"):
        return "TEXT"
    raise ValueError(f"unknown domain: {d}")


def keys_of(k):
    out = []
    if "PK" in k:
        out.append("PK")
    if "FK" in k:
        out.append("FK")
    if "AK" in k:
        out.append("UK")
    return out


tables = {}  # name -> dict(domain, label, cols)
for dom, fname in DOCS:
    lines = (MODELING / fname).read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        m = HEAD.match(lines[i])
        if not m:
            i += 1
            continue
        label, name = m.group(1), m.group(2)
        cols = []
        i += 1
        while i < len(lines) and not lines[i].startswith("| No |"):
            i += 1
        i += 2  # header + separator
        while i < len(lines) and lines[i].startswith("|"):
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            _, logical, col, domain, null, key = cells[:6]
            cols.append({
                "logical": logical,
                "name": col,
                "type": domain_token(domain.replace(" 🔒", "")),
                "nullable": null.startswith("Y"),
                "keys": keys_of(key),
                "enc": "🔒" in domain,
            })
            i += 1
        tables[name] = {"domain": dom, "label": label, "cols": cols}

# stubs: not designed yet (회색)
STUBS = {
    "grade": ("등급 (미설계)", [("grade_cd", "CODE", "등급코드")]),
    "seller": ("판매자 (미설계)", [("seller_id", "NUM", "판매자번호")]),
    "brand": ("브랜드 (미설계)", [("brand_id", "NUM", "브랜드번호")]),
    "customer_coupon": ("고객 쿠폰 (미설계)", [("customer_coupon_id", "NUM", "고객쿠폰번호")]),
}

# ---------- relationships ----------
# (parent, parent_card, child, child_card, identifying, label)
#   parent_card: '||' exactly one, '|o' zero or one
#   child_card:  'o{' zero or many, '|{' one or many, 'o|' zero or one
R = [
    # 고객
    ("grade", "||", "customer", "o{", False, "등급"),
    ("customer", "||", "customer_auth", "|{", True, "인증수단"),
    ("customer", "||", "customer_address", "o{", False, "배송지"),
    ("customer", "||", "customer_consent", "|{", True, "수신동의"),
    ("customer_consent", "||", "customer_consent_hist", "|{", False, "변경 이력"),
    ("customer", "||", "customer_body", "o|", True, "체형정보"),
    ("customer", "||", "customer_terms_agree", "|{", True, "동의"),
    ("terms", "||", "customer_terms_agree", "o{", True, "동의"),
    ("customer", "||", "customer_status_hist", "|{", False, "상태 이력"),
    ("customer", "||", "customer_withdrawal", "o|", True, "탈퇴"),
    # 카테고리
    ("category", "|o", "category", "o{", False, "상위-하위"),
    ("display_category", "|o", "display_category", "o{", False, "상위-하위"),
    ("display_category", "||", "display_category_link", "o{", True, "구성"),
    ("category", "||", "display_category_link", "o{", True, "구성"),
    ("display_category", "||", "display_category_product", "o{", True, "직접 지정"),
    ("product", "||", "display_category_product", "o{", True, "직접 지정"),
    # 상품
    ("category", "||", "product", "o{", False, "분류"),
    ("seller", "||", "product", "o{", False, "판매"),
    ("brand", "||", "product", "o{", False, "브랜드"),
    ("product", "||", "product_option_group", "o{", False, "옵션 그룹"),
    ("product_option_group", "||", "product_option_value", "|{", False, "옵션 값"),
    ("product", "||", "product_item", "|{", False, "단품"),
    ("product_item", "||", "product_item_option", "o{", True, "옵션 구성"),
    ("product_option_group", "||", "product_item_option", "|{", True, "옵션 구성"),
    ("product_option_value", "||", "product_item_option", "o{", False, "선택 값"),
    ("product", "||", "product_image", "|{", False, "이미지"),
    ("product_option_value", "|o", "product_image", "o{", False, "색상별 이미지"),
    ("attribute", "||", "attribute_option", "o{", False, "선택값"),
    ("category", "||", "category_attribute", "o{", True, "속성 지정"),
    ("attribute", "||", "category_attribute", "o{", True, "속성 지정"),
    ("product", "||", "product_attribute_value", "o{", True, "속성값"),
    ("attribute", "||", "product_attribute_value", "o{", True, "속성값"),
    ("attribute_option", "|o", "product_attribute_value", "o{", False, "선택"),
    ("product_option_value", "||", "product_size_measure", "o{", True, "실측"),
    ("attribute", "||", "product_size_measure", "o{", True, "실측"),
    ("product", "||", "product_price_hist", "|{", True, "가격 이력"),
    ("product_item", "||", "product_item_stock_hist", "o{", False, "재고 이력"),
    ("order_item", "|o", "product_item_stock_hist", "o{", False, "주문 참조"),
    ("product", "||", "product_status_hist", "|{", False, "상태 이력"),
    # 주문
    ("customer", "||", "cart_item", "o{", True, "장바구니"),
    ("product_item", "||", "cart_item", "o{", True, "담긴 단품"),
    ("customer", "||", "orders", "o{", False, "주문"),
    ("orders", "||", "order_seller", "|{", True, "판매자별"),
    ("seller", "||", "order_seller", "o{", True, "판매자별"),
    ("order_seller", "||", "order_item", "|{", False, "주문상품"),
    ("product_item", "||", "order_item", "o{", False, "주문 단품"),
    ("order_item", "||", "order_item_discount", "o{", True, "할인 배분"),
    ("customer_coupon", "|o", "order_item_discount", "o{", False, "쿠폰"),
    ("order_item", "||", "order_item_status_hist", "|{", False, "상태 이력"),
    # 결제·배송
    ("orders", "||", "payment", "o{", False, "결제"),
    ("payment", "||", "payment_card", "o|", True, "카드"),
    ("payment", "||", "payment_vbank", "o|", True, "가상계좌"),
    ("payment", "||", "payment_easy_pay", "o|", True, "간편결제"),
    ("payment", "||", "payment_transaction", "o{", False, "거래"),
    ("order_seller", "||", "shipment", "o{", False, "배송"),
    ("shipment", "||", "shipment_item", "|{", True, "배송상품"),
    ("order_item", "||", "shipment_item", "o{", True, "배송상품"),
    ("shipment", "||", "shipment_tracking_hist", "o{", False, "추적 이력"),
    ("orders", "||", "order_address_hist", "o{", False, "배송지 변경 이력"),
    # 클레임
    ("order_seller", "||", "claim", "o{", False, "클레임"),
    ("claim", "||", "claim_item", "|{", True, "클레임상품"),
    ("order_item", "||", "claim_item", "o{", True, "클레임상품"),
    ("product_item", "|o", "claim_item", "o{", False, "교환 단품"),
    ("claim", "||", "claim_status_hist", "|{", False, "상태 이력"),
    ("claim", "||", "claim_refund", "o{", True, "환불 배분"),
    ("payment", "||", "claim_refund", "o{", True, "환불 배분"),
    ("claim_refund", "|o", "payment_transaction", "o{", False, "환불 거래"),
    ("claim", "|o", "payment", "o{", False, "클레임 비용 결제"),
    ("claim", "|o", "shipment", "o{", False, "회수·재배송"),
]

for p, _, c, _, _, _ in R:
    for t in (p, c):
        assert t in tables or t in STUBS, f"relationship refers to unknown table {t}"

DOMAIN_LABEL = {"customer": "고객", "category": "카테고리", "product": "상품", "order": "주문", "payment": "결제·배송", "claim": "클레임"}


def entities_for(domain):
    """Tables fully drawn in this diagram + names drawn as PK-only stubs."""
    full = [t for t, v in tables.items() if domain in (None, v["domain"])]
    stubs = set()
    for p, _, c, _, _, _ in R:
        if p in full or c in full:
            for t in (p, c):
                if t not in full:
                    stubs.add(t)
    return full, sorted(stubs)


def stub_info(t):
    if t in STUBS:
        return STUBS[t]
    v = tables[t]
    pk = [(c["name"], c["type"], c["logical"]) for c in v["cols"] if "PK" in c["keys"]]
    return f"{v['label']} ({DOMAIN_LABEL[v['domain']]} 회차)", pk


# ---------- Mermaid ----------
def mermaid(domain, title):
    full, stubs = entities_for(domain)
    out = ["---", f"title: {title}", "---", "erDiagram"]
    for t in full:
        v = tables[t]
        out.append(f'    {t}["{v["label"]} {t}"] {{')
        for c in v["cols"]:
            keys = (" " + ", ".join(c["keys"])) if c["keys"] else ""
            note = c["logical"] + (" (선택)" if c["nullable"] else "") + (" 🔒" if c["enc"] else "")
            out.append(f'        {c["type"]} {c["name"]}{keys} "{note}"')
        out.append("    }")
    for t in stubs:
        label, pk = stub_info(t)
        out.append(f'    {t}["{label} {t}"] {{')
        for name, typ, logical in pk:
            out.append(f'        {typ} {name} PK "{logical}"')
        out.append("    }")
    drawn = set(full) | set(stubs)
    for p, pc, c, cc, ident, label in R:
        if p in drawn and c in drawn and (p in full or c in full):
            line = "--" if ident else ".."
            out.append(f'    {p} {pc}{line}{cc} {c} : "{label}"')
    return "\n".join(out) + "\n"


# ---------- draw.io ----------
W, HEADER, ROW, GAPX, GAPY = 330, 30, 22, 110, 50
FILL = {
    "customer": ("#dae8fc", "#6c8ebf"),
    "category": ("#d5e8d4", "#82b366"),
    "product": ("#ffe6cc", "#d79b00"),
    "order": ("#e1d5e7", "#9673a6"),
    "payment": ("#fff2cc", "#d6b656"),
    "claim": ("#f8cecc", "#b85450"),
    "stub": ("#f5f5f5", "#999999"),
}

# column layouts per domain (tables listed top to bottom per column)
LAYOUT = {
    "customer": [
        ["grade", "customer_withdrawal", "customer_body"],
        ["customer"],
        ["customer_auth", "customer_address", "customer_terms_agree", "customer_status_hist"],
        ["customer_consent", "customer_consent_hist", "terms"],
    ],
    "category": [
        ["category"],
        ["display_category_link", "product"],
        ["display_category", "display_category_product"],
    ],
    "product": [
        ["seller", "brand", "category", "category_attribute", "attribute", "attribute_option"],
        ["product", "product_price_hist", "product_status_hist", "product_attribute_value"],
        ["product_option_group", "product_option_value", "product_size_measure", "product_image"],
        ["product_item", "product_item_option", "product_item_stock_hist", "order_item"],
    ],
    "order": [
        ["customer", "cart_item", "product_item"],
        ["orders", "order_seller", "seller"],
        ["order_item", "order_item_status_hist"],
        ["order_item_discount", "customer_coupon"],
    ],
    "payment": [
        ["orders", "order_address_hist"],
        ["payment", "payment_transaction"],
        ["payment_card", "payment_vbank", "payment_easy_pay"],
        ["order_seller", "shipment", "shipment_tracking_hist"],
        ["shipment_item", "order_item"],
    ],
    "claim": [
        ["order_seller", "order_item", "product_item"],
        ["claim", "claim_status_hist", "shipment"],
        ["claim_item", "claim_refund", "payment"],
        ["payment_transaction"],
    ],
}

ARROW = {"||": "ERmandOne", "|o": "ERzeroToOne", "o|": "ERzeroToOne", "o{": "ERzeroToMany", "|{": "ERoneToMany"}


class Page:
    def __init__(self, name):
        self.name = name
        self.cells = []
        self.n = 2
        self.ids = {}

    def nid(self):
        self.n += 1
        return f"c{self.n}"

    def table(self, t, x, y, stub, domain):
        if stub:
            label, pk = stub_info(t)
            rows = [("PK", f"{n} : {lg}", False) for n, _, lg in pk]
            fill, stroke = FILL["stub"]
            dashed = "dashed=1;"
        else:
            v = tables[t]
            label = v["label"]
            rows = []
            for c in v["cols"]:
                k = ",".join(c["keys"])
                text = f"{c['name']} : {c['logical']}" + (" (?)" if c["nullable"] else "")
                rows.append((k, text, "PK" in c["keys"]))
            fill, stroke = FILL[domain]
            dashed = ""
        h = HEADER + ROW * len(rows) + 8
        tid = self.nid()
        self.ids[t] = tid
        self.cells.append(
            f'<mxCell id="{tid}" value="{escape(label)}&lt;br&gt;&lt;font style=&quot;font-size:10px&quot;&gt;{t}&lt;/font&gt;" '
            f'style="swimlane;fontStyle=1;html=1;childLayout=stackLayout;horizontal=1;startSize={HEADER};'
            f'horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=1;marginBottom=0;'
            f'fillColor={fill};strokeColor={stroke};swimlaneFillColor=#ffffff;{dashed}rounded=1;arcSize=4;" '
            f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{W}" height="{h}" as="geometry"/></mxCell>'
        )
        cy = HEADER
        for k, text, is_pk in rows:
            rid = self.nid()
            style = ("text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;spacingLeft=6;"
                     "overflow=hidden;rotatable=0;points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontSize=11;"
                     + ("fontStyle=5;" if is_pk else ""))
            val =(f"&lt;b&gt;{escape(k)}&lt;/b&gt;&amp;nbsp;" if k else "&amp;nbsp;&amp;nbsp;&amp;nbsp;&amp;nbsp;") + escape(escape(text))
            self.cells.append(
                f'<mxCell id="{rid}" value="{val}" style="{style}" vertex="1" parent="{tid}">'
                f'<mxGeometry y="{cy}" width="{W}" height="{ROW}" as="geometry"/></mxCell>'
            )
            cy += ROW
        return h

    def edge(self, p, pc, c, cc, ident, label):
        s, t = self.ids[p], self.ids[c]
        eid = self.nid()
        base = (f"html=1;endArrow={ARROW[cc]};startArrow={ARROW[pc]};endFill=0;startFill=0;"
                f"endSize=10;startSize=10;fontSize=10;{'' if ident else 'dashed=1;'}")
        if p == c:  # 재귀적 관계: 오른쪽으로 나갔다가 돌아오는 고리
            style = base + "edgeStyle=orthogonalEdgeStyle;rounded=0;exitX=1;exitY=0.15;exitDx=0;exitDy=0;entryX=1;entryY=0.35;entryDx=0;entryDy=0;"
            geo = ('<mxGeometry relative="1" as="geometry"><Array as="points">'
                   '<mxPoint x="__X1__" y="__Y1__"/><mxPoint x="__X1__" y="__Y2__"/></Array></mxGeometry>')
            self.cells.append(("SELF", eid, s, label, style, geo))
            return
        style = base + "edgeStyle=entityRelationEdgeStyle;"
        self.cells.append(
            f'<mxCell id="{eid}" value="{escape(label)}" style="{style}" edge="1" parent="1" source="{s}" target="{t}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>'
        )

    def legend(self, x, y):
        lid = self.nid()
        text = ("&lt;b&gt;범례&lt;/b&gt;&lt;br&gt;"
                "실선 = 식별 관계 / 점선 = 비식별 관계&lt;br&gt;"
                "선 끝: | 필수, O 선택, 까마귀발 = M(多)&lt;br&gt;"
                "PK 기본 키 · FK 참조 키 · UK 대체 식별자 · (?) 선택(NULL 허용)&lt;br&gt;"
                "파랑 고객 · 초록 카테고리 · 주황 상품 · 보라 주문 · 노랑 결제·배송 · 빨강 클레임 · 회색 점선 = 미설계/다른 회차&lt;br&gt;"
                "시스템 컬럼 4개(created_by, created_at, updated_by, updated_at)는 생략")
        self.cells.append(
            f'<mxCell id="{lid}" value="{text}" style="text;html=1;align=left;verticalAlign=top;spacing=8;'
            f'fillColor=#ffffff;strokeColor=#666666;fontSize=12;" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="520" height="120" as="geometry"/></mxCell>'
        )

    def xml(self, geom):
        body = []
        for c in self.cells:
            if isinstance(c, tuple):
                _, eid, s, label, style, geo = c
                gx, gy, gw, gh = geom[s]
                geo = (geo.replace("__X1__", str(gx + gw + 40))
                       .replace("__Y1__", str(gy + int(gh * 0.15)))
                       .replace("__Y2__", str(gy + int(gh * 0.35))))
                body.append(f'<mxCell id="{eid}" value="{escape(label)}" style="{style}" edge="1" parent="1" '
                            f'source="{s}" target="{s}">{geo}</mxCell>')
            else:
                body.append(c)
        return (f'<diagram id="{self.name}" name="{self.name}"><mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" '
                f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" math="0" shadow="0">'
                f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>{"".join(body)}</root></mxGraphModel></diagram>')


def build_page(name, domains):
    page = Page(name)
    geom = {}
    real = {t for t, v in tables.items() if v["domain"] in domains}
    x0 = 0
    legend_y = 0
    for d in domains:
        cols = LAYOUT[d]
        for ci, col in enumerate(cols):
            y = 0
            for t in col:
                if t in page.ids:
                    continue
                if t in real and tables[t]["domain"] != d:  # drawn in full by its own domain block
                    continue
                stub = t not in real
                x = x0 + ci * (W + GAPX)
                h = page.table(t, x, y, stub, d)
                geom[page.ids[t]] = (x, y, W, h)
                y += h + GAPY
            legend_y = max(legend_y, y)
        x0 += len(cols) * (W + GAPX) + 120
    drawn = set(page.ids)
    for p, pc, c, cc, ident, label in R:
        if p in drawn and c in drawn and (p in real or c in real):
            page.edge(p, pc, c, cc, ident, label)
    page.legend(0, legend_y + 40)
    return page.xml(geom)


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / "erd_전체.mmd").write_text(mermaid(None, "무신사 기반 쇼핑몰 ERD - 고객·카테고리·상품·주문·결제·배송·클레임"), encoding="utf-8")
    (OUT / "erd_01_고객.mmd").write_text(mermaid("customer", "1회차 고객 ERD"), encoding="utf-8")
    (OUT / "erd_02_카테고리.mmd").write_text(mermaid("category", "2회차 카테고리 ERD"), encoding="utf-8")
    (OUT / "erd_03_상품.mmd").write_text(mermaid("product", "3회차 상품 ERD"), encoding="utf-8")
    (OUT / "erd_04_주문.mmd").write_text(mermaid("order", "4회차 장바구니·주문 ERD"), encoding="utf-8")
    (OUT / "erd_05_결제_배송.mmd").write_text(mermaid("payment", "5회차 결제·배송 ERD"), encoding="utf-8")
    (OUT / "erd_06_클레임.mmd").write_text(mermaid("claim", "6회차 클레임 ERD"), encoding="utf-8")
    pages = [
        build_page("전체", ["customer", "category", "product", "order", "payment", "claim"]),
        build_page("고객", ["customer"]),
        build_page("카테고리", ["category"]),
        build_page("상품", ["product"]),
        build_page("주문", ["order"]),
        build_page("결제·배송", ["payment"]),
        build_page("클레임", ["claim"]),
    ]
    (OUT / "erd_전체.drawio").write_text(
        f'<mxfile host="app.diagrams.net" type="device">{"".join(pages)}</mxfile>\n', encoding="utf-8")
    counts = {d: sum(1 for v in tables.values() if v["domain"] == d) for d, _ in DOCS}
    print("tables:", counts, "total", len(tables), "relationships:", len(R))


main()
