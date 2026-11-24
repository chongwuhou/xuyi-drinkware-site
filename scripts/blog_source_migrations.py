"""Reviewed, idempotent Blog source migrations.

These are data migrations, not renderer fallbacks.  A migration may change a
published D1 record only when the current value is the exact reviewed defect
that it was written to repair.  If an owner has changed the record in any
other way, the migration fails closed and leaves the content untouched.
"""

from __future__ import annotations


BICYCLE_SLUG = "bicycle-shop-water-bottle-cage-fit-wholesale-buying"

ENGLISH_BICYCLE_TABLE_OLD = [
    [
        "Segment cycling retail customers before ordering",
        "Buyer roster or demand forecast",
        "Approve quantity",
    ],
    [
        "Test actual bicycle cage fit and frame clearance",
        "Signed assembled bottle sample",
        "Approve configuration",
    ],
    [
        "Check closure handling and complete sample parts",
        "Authorized art and variant plan",
        "Approve artwork",
    ],
    [
        "Plan store logos, colors and shelf barcode labels",
        "Written care and component rules",
        "Approve procedure",
    ],
    [
        "Compare shelf margin and seasonal assortment risks",
        "Equivalent landed-cost quote",
        "Approve commercial terms",
    ],
    [
        "Inspect wholesale cartons and test retail labeling",
        "Receiving checks and carton record",
        "Approve receipt",
    ],
]

ENGLISH_BICYCLE_TABLE_NEW = [
    [
        "Segment cycling retail customers before ordering",
        "Buyer roster or demand forecast",
        "Approve quantity",
    ],
    [
        "Test actual bicycle cage fit and frame clearance",
        "Signed assembled bottle sample",
        "Approve configuration",
    ],
    [
        "Check closure handling and complete sample parts",
        "Complete cap, seal and removable-part sample review",
        "Approve closure and care instructions",
    ],
    [
        "Plan store logos, colors and shelf barcode labels",
        "Approved artwork, color split and barcode layout",
        "Approve artwork and label set",
    ],
    [
        "Compare shelf margin and seasonal assortment risks",
        "Equivalent landed-cost quote",
        "Approve commercial terms",
    ],
    [
        "Inspect wholesale cartons and test retail labeling",
        "Receiving checks and carton record",
        "Approve receipt",
    ],
]


# The translated tables were produced by a broken row/column translation
# routine.  Keep the exact observed matrix as the guard so a later owner edit
# is never mistaken for this defect.
LOCALIZED_BICYCLE_TABLES = {
    "es": {
        "head_old": [
            "Planificar la demanda y la distribución",
            "Revisar la muestra completa en el entorno real",
            "Aprobar los logotipos y las variantes",
        ],
        "rows_old": [
            ["Planificar la demanda y la distribución", "Revisar la muestra completa en el entorno real", "Aprobar los logotipos y las variantes"],
            ["Revisar la muestra completa en el entorno real", "Aprobar los logotipos y las variantes", "Definir higiene, piezas y responsabilidades"],
            ["Aprobar los logotipos y las variantes", "Definir higiene, piezas y responsabilidades", "Comparar los costes entregados"],
            ["Definir higiene, piezas y responsabilidades", "Comparar los costes entregados", "Verificar el embalaje y la recepción"],
            ["Comparar los costes entregados", "Verificar el embalaje y la recepción", "Guardar el registro de reposición"],
            ["Verificar el embalaje y la recepción", "Guardar el registro de reposición", "Planificar la demanda y la distribución"],
        ],
        "head_new": ["Etapa", "Evidencia requerida", "Aprobación"],
        "rows_new": [
            ["Segmentar a los clientes ciclistas antes de pedir", "Registro de compradores o previsión de demanda", "Aprobar cantidad"],
            ["Probar el ajuste en el portabidón y el espacio del cuadro", "Muestra completa ensamblada y firmada", "Aprobar configuración"],
            ["Comprobar el cierre y todas las piezas de la muestra", "Revisión de tapa, junta y piezas desmontables", "Aprobar cierre e instrucciones de cuidado"],
            ["Planificar logotipos, colores y códigos de barras del estante", "Diseño aprobado, reparto de colores y formato de código de barras", "Aprobar diseño y etiquetado"],
            ["Comparar el margen del estante y el riesgo estacional del surtido", "Cotización del coste total entregado", "Aprobar condiciones comerciales"],
            ["Inspeccionar las cajas al por mayor y el etiquetado minorista", "Control de recepción y registro de cajas", "Aprobar recepción"],
        ],
    },
    "pt": {
        "head_old": ["Definir a demanda e a distribuição", "Testar a amostra completa em uso real", "Aprovar marca e variantes"],
        "rows_old": [
            ["Definir a demanda e a distribuição", "Testar a amostra completa em uso real", "Aprovar marca e variantes"],
            ["Testar a amostra completa em uso real", "Aprovar marca e variantes", "Definir limpeza, peças e responsabilidades"],
            ["Aprovar marca e variantes", "Definir limpeza, peças e responsabilidades", "Comparar o custo total entregue"],
            ["Definir limpeza, peças e responsabilidades", "Comparar o custo total entregue", "Inspecionar caixas e recebimento"],
            ["Comparar o custo total entregue", "Inspecionar caixas e recebimento", "Documentar o pedido seguinte"],
            ["Inspecionar caixas e recebimento", "Documentar o pedido seguinte", "Definir a demanda e a distribuição"],
        ],
        "head_new": ["Etapa", "Evidência necessária", "Aprovação"],
        "rows_new": [
            ["Segmentar clientes de ciclismo antes do pedido", "Lista de compradores ou previsão de demanda", "Aprovar quantidade"],
            ["Testar o encaixe no suporte e a folga no quadro", "Amostra completa montada e assinada", "Aprovar configuração"],
            ["Verificar o fechamento e todas as peças da amostra", "Revisão da tampa, vedação e peças removíveis", "Aprovar fechamento e instruções de cuidado"],
            ["Planejar logotipos, cores e códigos de barras da prateleira", "Arte aprovada, divisão de cores e layout do código de barras", "Aprovar arte e etiquetagem"],
            ["Comparar margem de prateleira e riscos sazonais do mix", "Cotação do custo total entregue", "Aprovar condições comerciais"],
            ["Inspecionar caixas de atacado e a etiquetagem para varejo", "Controle de recebimento e registro da caixa", "Aprovar recebimento"],
        ],
    },
    "ru": {
        "head_old": ["Рассчитать спрос и распределение", "Проверить полный образец на месте", "Согласовать брендирование и варианты"],
        "rows_old": [
            ["Рассчитать спрос и распределение", "Проверить полный образец на месте", "Согласовать брендирование и варианты"],
            ["Проверить полный образец на месте", "Согласовать брендирование и варианты", "Определить уход и заменяемые детали"],
            ["Согласовать брендирование и варианты", "Определить уход и заменяемые детали", "Сравнить полную стоимость поставки"],
            ["Определить уход и заменяемые детали", "Сравнить полную стоимость поставки", "Проверить маркировку и приемку"],
            ["Сравнить полную стоимость поставки", "Проверить маркировку и приемку", "Сохранить данные для повторной закупки"],
            ["Проверить маркировку и приемку", "Сохранить данные для повторной закупки", "Рассчитать спрос и распределение"],
        ],
        "head_new": ["Этап", "Требуемое подтверждение", "Согласование"],
        "rows_new": [
            ["Сегментировать покупателей велосипедных магазинов до заказа", "Список покупателей или прогноз спроса", "Согласовать количество"],
            ["Проверить посадку в держателе и зазор у рамы", "Подписанный полный собранный образец", "Согласовать конфигурацию"],
            ["Проверить крышку и все детали образца", "Проверка крышки, уплотнителя и съемных деталей", "Согласовать закрытие и инструкции по уходу"],
            ["Спланировать логотипы, цвета и штрихкоды на полке", "Утвержденный макет, распределение цветов и формат штрихкода", "Согласовать макет и маркировку"],
            ["Сравнить полочную маржу и сезонные риски ассортимента", "Расчет полной стоимости поставки", "Согласовать коммерческие условия"],
            ["Проверить оптовые коробки и розничную маркировку", "Приемочный контроль и запись по коробам", "Согласовать приемку"],
        ],
    },
    "tr": {
        "head_old": ["Talebi ve dağıtımı planlayın", "Gerçek ortamda tam numuneyi kontrol edin", "Marka izinleri ve varyantları onaylayın"],
        "rows_old": [
            ["Talebi ve dağıtımı planlayın", "Gerçek ortamda tam numuneyi kontrol edin", "Marka izinleri ve varyantları onaylayın"],
            ["Gerçek ortamda tam numuneyi kontrol edin", "Marka izinleri ve varyantları onaylayın", "Temizlik ve yedek parça sorumluluğunu belirleyin"],
            ["Marka izinleri ve varyantları onaylayın", "Temizlik ve yedek parça sorumluluğunu belirleyin", "Toplam teslim maliyetini karşılaştırın"],
            ["Temizlik ve yedek parça sorumluluğunu belirleyin", "Toplam teslim maliyetini karşılaştırın", "Kolileri ve teslimatı doğrulayın"],
            ["Toplam teslim maliyetini karşılaştırın", "Kolileri ve teslimatı doğrulayın", "Yeniden sipariş kayıtlarını saklayın"],
            ["Kolileri ve teslimatı doğrulayın", "Yeniden sipariş kayıtlarını saklayın", "Talebi ve dağıtımı planlayın"],
        ],
        "head_new": ["Aşama", "Gerekli kanıt", "Onay"],
        "rows_new": [
            ["Bisiklet mağazası müşterilerini siparişten önce segmentlere ayırın", "Alıcı listesi veya talep tahmini", "Miktarı onaylayın"],
            ["Şişenin kafese oturuşunu ve kadro boşluğunu test edin", "İmzalı, monte edilmiş tam numune", "Konfigürasyonu onaylayın"],
            ["Kapağın kapanmasını ve numunenin tüm parçalarını kontrol edin", "Kapak, conta ve çıkarılabilir parçaların incelemesi", "Kapanış ve bakım talimatlarını onaylayın"],
            ["Mağaza logolarını, renklerini ve raf barkodlarını planlayın", "Onaylı tasarım, renk dağılımı ve barkod düzeni", "Tasarım ve etiketlemeyi onaylayın"],
            ["Raf marjını ve sezonluk ürün karması risklerini karşılaştırın", "Teslim edilmiş toplam maliyet teklifi", "Ticari koşulları onaylayın"],
            ["Toptan kolileri ve perakende etiketlerini inceleyin", "Teslim alma kontrolü ve koli kaydı", "Teslim almayı onaylayın"],
        ],
    },
}


def table_state(rows: object) -> tuple[tuple[str, ...], ...] | None:
    if not isinstance(rows, list) or not all(isinstance(row, list) and len(row) == 3 for row in rows):
        return None
    return tuple(tuple(str(cell).strip() for cell in row) for row in rows)


def repair_english_table(post: dict) -> str:
    """Return ``changed``, ``already-correct`` or raise on an owner conflict."""
    table = post.get("buyerDecisionTable")
    if not isinstance(table, dict):
        raise ValueError("English Blog source has no buyerDecisionTable")
    current = table_state(table.get("rows"))
    old = table_state(ENGLISH_BICYCLE_TABLE_OLD)
    new = table_state(ENGLISH_BICYCLE_TABLE_NEW)
    if current == new:
        return "already-correct"
    if current != old:
        raise ValueError("English bicycle decision table differs from the reviewed defect; refusing to overwrite owner content")
    table["rows"] = [list(row) for row in ENGLISH_BICYCLE_TABLE_NEW]
    return "changed"


def html_escape(value: str) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def render_table(head: list[str], rows: list[list[str]]) -> str:
    header = "".join(f'<th scope="col">{html_escape(cell)}</th>' for cell in head)
    body = "".join(
        "<tr>" + f'<th scope="row">{html_escape(row[0])}</th>'
        + "".join(f"<td>{html_escape(cell)}</td>" for cell in row[1:])
        + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"


def extract_table_cells(html: str) -> tuple[list[str], list[list[str]]] | None:
    import html as html_module
    import re

    match = re.search(r"<table\b[^>]*>[\s\S]*?</table>", html, flags=re.IGNORECASE)
    if not match:
        return None
    table_html = match.group(0)

    def text(value: str) -> str:
        value = re.sub(r"<[^>]+>", "", value)
        value = html_module.unescape(value)
        return re.sub(r"\s+", " ", value).strip()

    head_match = re.search(r"<thead\b[^>]*>[\s\S]*?</thead>", table_html, flags=re.IGNORECASE)
    body_match = re.search(r"<tbody\b[^>]*>[\s\S]*?</tbody>", table_html, flags=re.IGNORECASE)
    if not head_match or not body_match:
        return None
    head = [text(value) for value in re.findall(r"<th\b[^>]*>([\s\S]*?)</th>", head_match.group(0), flags=re.IGNORECASE)]
    rows = []
    for row in re.findall(r"<tr\b[^>]*>([\s\S]*?)</tr>", body_match.group(0), flags=re.IGNORECASE):
        cells = [text(value) for value in re.findall(r"<(?:th|td)\b[^>]*>([\s\S]*?)</(?:th|td)>", row, flags=re.IGNORECASE)]
        rows.append(cells)
    return head, rows


def repair_localized_table(main_html: str, locale: str) -> tuple[str, str]:
    import re

    spec = LOCALIZED_BICYCLE_TABLES.get(locale)
    if not spec:
        raise ValueError(f"No reviewed bicycle table migration for locale {locale}")
    current = extract_table_cells(main_html)
    if not current:
        raise ValueError(f"{locale} Blog translation has no parseable decision table")
    head, rows = current
    if head == spec["head_new"] and rows == spec["rows_new"]:
        return main_html, "already-correct"
    if head != spec["head_old"] or rows != spec["rows_old"]:
        raise ValueError(f"{locale} bicycle decision table differs from the reviewed defect; refusing to overwrite owner content")
    replacement = render_table(spec["head_new"], spec["rows_new"])
    updated, count = re.subn(r"<table\b[^>]*>[\s\S]*?</table>", replacement, main_html, count=1, flags=re.IGNORECASE)
    if count != 1:
        raise ValueError(f"{locale} Blog translation table replacement was not unique")
    return updated, "changed"


