// Reviewed Blog source repairs.  This module accepts no arbitrary copy: it
// only repairs the exact bicycle decision-table defect after a full old-value
// match.  It is called by the existing generic D1/CMS Blog batch entrypoint.
const SLUG = "bicycle-shop-water-bottle-cage-fit-wholesale-buying";
const locales = ["es", "pt", "ru", "tr"];
const ENGLISH_OLD = [
 ["Segment cycling retail customers before ordering","Buyer roster or demand forecast","Approve quantity"],
 ["Test actual bicycle cage fit and frame clearance","Signed assembled bottle sample","Approve configuration"],
 ["Check closure handling and complete sample parts","Authorized art and variant plan","Approve artwork"],
 ["Plan store logos, colors and shelf barcode labels","Written care and component rules","Approve procedure"],
 ["Compare shelf margin and seasonal assortment risks","Equivalent landed-cost quote","Approve commercial terms"],
 ["Inspect wholesale cartons and test retail labeling","Receiving checks and carton record","Approve receipt"]
];
const ENGLISH_NEW = [
 ["Segment cycling retail customers before ordering","Buyer roster or demand forecast","Approve quantity"],
 ["Test actual bicycle cage fit and frame clearance","Signed assembled bottle sample","Approve configuration"],
 ["Check closure handling and complete sample parts","Complete cap, seal and removable-part sample review","Approve closure and care instructions"],
 ["Plan store logos, colors and shelf barcode labels","Approved artwork, color split and barcode layout","Approve artwork and label set"],
 ["Compare shelf margin and seasonal assortment risks","Equivalent landed-cost quote","Approve commercial terms"],
 ["Inspect wholesale cartons and test retail labeling","Receiving checks and carton record","Approve receipt"]
];
const LOCALIZED = {
 es: {
  oldHead:["Planificar la demanda y la distribución","Revisar la muestra completa en el entorno real","Aprobar los logotipos y las variantes"],
  oldRows:[["Planificar la demanda y la distribución","Revisar la muestra completa en el entorno real","Aprobar los logotipos y las variantes"],["Revisar la muestra completa en el entorno real","Aprobar los logotipos y las variantes","Definir higiene, piezas y responsabilidades"],["Aprobar los logotipos y las variantes","Definir higiene, piezas y responsabilidades","Comparar los costes entregados"],["Definir higiene, piezas y responsabilidades","Comparar los costes entregados","Verificar el embalaje y la recepción"],["Comparar los costes entregados","Verificar el embalaje y la recepción","Guardar el registro de reposición"],["Verificar el embalaje y la recepción","Guardar el registro de reposición","Planificar la demanda y la distribución"]],
  head:["Etapa","Evidencia requerida","Aprobación"],
  rows:[["Segmentar a los clientes ciclistas antes de pedir","Registro de compradores o previsión de demanda","Aprobar cantidad"],["Probar el ajuste en el portabidón y el espacio del cuadro","Muestra completa ensamblada y firmada","Aprobar configuración"],["Comprobar el cierre y todas las piezas de la muestra","Revisión de tapa, junta y piezas desmontables","Aprobar cierre e instrucciones de cuidado"],["Planificar logotipos, colores y códigos de barras del estante","Diseño aprobado, reparto de colores y formato de código de barras","Aprobar diseño y etiquetado"],["Comparar el margen del estante y el riesgo estacional del surtido","Cotización del coste total entregado","Aprobar condiciones comerciales"],["Inspeccionar las cajas al por mayor y el etiquetado minorista","Control de recepción y registro de cajas","Aprobar recepción"]]
 },
 pt: {
  oldHead:["Definir a demanda e a distribuição","Testar a amostra completa em uso real","Aprovar marca e variantes"],
  oldRows:[["Definir a demanda e a distribuição","Testar a amostra completa em uso real","Aprovar marca e variantes"],["Testar a amostra completa em uso real","Aprovar marca e variantes","Definir limpeza, peças e responsabilidades"],["Aprovar marca e variantes","Definir limpeza, peças e responsabilidades","Comparar o custo total entregue"],["Definir limpeza, peças e responsabilidades","Comparar o custo total entregue","Inspecionar caixas e recebimento"],["Comparar o custo total entregue","Inspecionar caixas e recebimento","Documentar o pedido seguinte"],["Inspecionar caixas e recebimento","Documentar o pedido seguinte","Definir a demanda e a distribuição"]],
  head:["Etapa","Evidência necessária","Aprovação"],
  rows:[["Segmentar clientes de ciclismo antes do pedido","Lista de compradores ou previsão de demanda","Aprovar quantidade"],["Testar o encaixe no suporte e a folga no quadro","Amostra completa montada e assinada","Aprovar configuração"],["Verificar o fechamento e todas as peças da amostra","Revisão da tampa, vedação e peças removíveis","Aprovar fechamento e instruções de cuidado"],["Planejar logotipos, cores e códigos de barras da prateleira","Arte aprovada, divisão de cores e layout do código de barras","Aprovar arte e etiquetagem"],["Comparar margem de prateleira e riscos sazonais do mix","Cotação do custo total entregue","Aprovar condições comerciais"],["Inspecionar caixas de atacado e a etiquetagem para varejo","Controle de recebimento e registro da caixa","Aprovar recebimento"]]
 },
 ru: {
  oldHead:["Рассчитать спрос и распределение","Проверить полный образец на месте","Согласовать брендирование и варианты"],
  oldRows:[["Рассчитать спрос и распределение","Проверить полный образец на месте","Согласовать брендирование и варианты"],["Проверить полный образец на месте","Согласовать брендирование и варианты","Определить уход и заменяемые детали"],["Согласовать брендирование и варианты","Определить уход и заменяемые детали","Сравнить полную стоимость поставки"],["Определить уход и заменяемые детали","Сравнить полную стоимость поставки","Проверить маркировку и приемку"],["Сравнить полную стоимость поставки","Проверить маркировку и приемку","Сохранить данные для повторной закупки"],["Проверить маркировку и приемку","Сохранить данные для повторной закупки","Рассчитать спрос и распределение"]],
  head:["Этап","Требуемое подтверждение","Согласование"],
  rows:[["Сегментировать покупателей велосипедных магазинов до заказа","Список покупателей или прогноз спроса","Согласовать количество"],["Проверить посадку в держателе и зазор у рамы","Подписанный полный собранный образец","Согласовать конфигурацию"],["Проверить крышку и все детали образца","Проверка крышки, уплотнителя и съемных деталей","Согласовать закрытие и инструкции по уходу"],["Спланировать логотипы, цвета и штрихкоды на полке","Утвержденный макет, распределение цветов и формат штрихкода","Согласовать макет и маркировку"],["Сравнить полочную маржу и сезонные риски ассортимента","Расчет полной стоимости поставки","Согласовать коммерческие условия"],["Проверить оптовые коробки и розничную маркировку","Приемочный контроль и запись по коробам","Согласовать приемку"]]
 },
 tr: {
  oldHead:["Talebi ve dağıtımı planlayın","Gerçek ortamda tam numuneyi kontrol edin","Marka izinleri ve varyantları onaylayın"],
  oldRows:[["Talebi ve dağıtımı planlayın","Gerçek ortamda tam numuneyi kontrol edin","Marka izinleri ve varyantları onaylayın"],["Gerçek ortamda tam numuneyi kontrol edin","Marka izinleri ve varyantları onaylayın","Temizlik ve yedek parça sorumluluğunu belirleyin"],["Marka izinleri ve varyantları onaylayın","Temizlik ve yedek parça sorumluluğunu belirleyin","Toplam teslim maliyetini karşılaştırın"],["Temizlik ve yedek parça sorumluluğunu belirleyin","Toplam teslim maliyetini karşılaştırın","Kolileri ve teslimatı doğrulayın"],["Toplam teslim maliyetini karşılaştırın","Kolileri ve teslimatı doğrulayın","Yeniden sipariş kayıtlarını saklayın"],["Kolileri ve teslimatı doğrulayın","Yeniden sipariş kayıtlarını saklayın","Talebi ve dağıtımı planlayın"]],
  head:["Aşama","Gerekli kanıt","Onay"],
  rows:[["Bisiklet mağazası müşterilerini siparişten önce segmentlere ayırın","Alıcı listesi veya talep tahmini","Miktarı onaylayın"],["Şişenin kafese oturuşunu ve kadro boşluğunu test edin","İmzalı, monte edilmiş tam numune","Konfigürasyonu onaylayın"],["Kapağın kapanmasını ve numunenin tüm parçalarını kontrol edin","Kapak, conta ve çıkarılabilir parçaların incelemesi","Kapanış ve bakım talimatlarını onaylayın"],["Mağaza logolarını, renklerini ve raf barkodlarını planlayın","Onaylı tasarım, renk dağılımı ve barkod düzeni","Tasarım ve etiketlemeyi onaylayın"],["Raf marjını ve sezonluk ürün karması risklerini karşılaştırın","Teslim edilmiş toplam maliyet teklifi","Ticari koşulları onaylayın"],["Toptan kolileri ve perakende etiketlerini inceleyin","Teslim alma kontrolü ve koli kaydı","Teslim almayı onaylayın"]]
 }
};

const sameRows=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const decode=(value)=>String(value).replace(/<[^>]+>/g,"").replace(/&amp;/g,"&").replace(/&lt;/g,"<").replace(/&gt;/g,">").replace(/&quot;/g,'"').replace(/&#39;|&#x27;/g,"'").replace(/\s+/g," ").trim();
function readTable(html){
 const match=String(html).match(/<table\b[^>]*>[\s\S]*?<\/table>/i);if(!match)return null;
 const table=match[0],head=table.match(/<thead\b[^>]*>[\s\S]*?<\/thead>/i),body=table.match(/<tbody\b[^>]*>[\s\S]*?<\/tbody>/i);if(!head||!body)return null;
 const cells=part=>[...part.matchAll(/<(?:th|td)\b[^>]*>([\s\S]*?)<\/(?:th|td)>/gi)].map(x=>decode(x[1]));
 const rows=[...body[0].matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)].map(x=>cells(x[1]));
 return {match:match[0],head:cells(head[0]),rows};
}
const esc=value=>String(value).replace(/[&<>"']/g,x=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]));
function tableHtml(head,rows){return "<table><thead><tr>"+head.map(x=>'<th scope="col">'+esc(x)+"</th>").join("")+"</tr></thead><tbody>"+rows.map(row=>"<tr><th scope=\"row\">"+esc(row[0])+"</th>"+row.slice(1).map(x=>"<td>"+esc(x)+"</td>").join("")+"</tr>").join("")+"</tbody></table>";}
function repairLocaleHtml(html,locale){
 const spec=LOCALIZED[locale],parsed=readTable(html);if(!spec||!parsed)throw Error("Missing parseable reviewed table: "+locale);
 if(sameRows(parsed.head,spec.head)&&sameRows(parsed.rows,spec.rows))return {html,state:"already-correct"};
 if(!sameRows(parsed.head,spec.oldHead)||!sameRows(parsed.rows,spec.oldRows))throw Error("Reviewed table guard mismatch: "+locale);
 return {html:String(html).replace(parsed.match,tableHtml(spec.head,spec.rows)),state:"changed"};
}

export async function repairReviewedBlogSource(db){
 const source=await db.prepare("SELECT status,content_json FROM xuyi_blog_posts WHERE slug=?").bind(SLUG).first();
 if(!source||source.status!=="published")throw Error("Reviewed Blog source is not published: "+SLUG);
 let post;try{post=JSON.parse(source.content_json||"")}catch{throw Error("Reviewed Blog source JSON is invalid")}
 const changes=[],states={};
 const oldEnglish=JSON.stringify(post?.buyerDecisionTable?.rows||[]);
 if(sameRows(post?.buyerDecisionTable?.rows,ENGLISH_NEW))states.en="already-correct";
 else if(sameRows(post?.buyerDecisionTable?.rows,ENGLISH_OLD)){post.buyerDecisionTable.rows=ENGLISH_NEW;states.en="changed";changes.push({kind:"en",old:source.content_json,new:JSON.stringify(post),slug:SLUG});}
 else throw Error("Reviewed table guard mismatch: en");
 const resource="page:/blog/"+SLUG+"/";
 const translations=(await db.prepare("SELECT locale,translated_json FROM xuyi_translation_overrides WHERE resource_id=? AND locale IN ('es','pt','ru','tr')").bind(resource).all()).results||[];
 const byLocale=new Map(translations.map(row=>[String(row.locale),row]));
 for(const locale of locales){
  const row=byLocale.get(locale);if(!row)throw Error("Missing reviewed Blog translation: "+locale);
  let content;try{content=JSON.parse(row.translated_json||"")}catch{throw Error("Invalid reviewed Blog translation JSON: "+locale)}
  const repaired=repairLocaleHtml(content.mainHtml||"",locale);states[locale]=repaired.state;
  if(repaired.state==="changed"){content.mainHtml=repaired.html;changes.push({kind:"locale",locale,resource,old:row.translated_json,new:JSON.stringify(content)});}
 }
 if(!changes.length)return {success:true,sourceRepair:true,changed:0,states};
 const guards=[];const guardArgs=[];
 for(const item of changes){if(item.kind==="en"){guards.push("(SELECT COUNT(*) FROM xuyi_blog_posts WHERE slug=? AND status='published' AND content_json=?)");guardArgs.push(item.slug,item.old)}else{guards.push("(SELECT COUNT(*) FROM xuyi_translation_overrides WHERE resource_id=? AND locale=? AND translated_json=?)");guardArgs.push(item.resource,item.locale,item.old)}}
 const guard=guards.join("+")+"="+changes.length+" AND EXISTS (SELECT 1 FROM site_state WHERE key='publish_revision')";
 const statements=[db.prepare("UPDATE site_state SET value=CAST(CAST(value AS INTEGER)+1 AS TEXT),updated_at=CURRENT_TIMESTAMP WHERE key='publish_revision' AND ("+guard+")").bind(...guardArgs)];
 for(const item of changes){
  if(item.kind==="en")statements.push(db.prepare("UPDATE xuyi_blog_posts SET content_json=?,updated_at=CURRENT_TIMESTAMP WHERE slug=? AND status='published' AND content_json=? AND ("+guard+")").bind(item.new,item.slug,item.old,...guardArgs));
  else statements.push(db.prepare("UPDATE xuyi_translation_overrides SET translated_json=?,reviewed_at=CURRENT_TIMESTAMP WHERE resource_id=? AND locale=? AND translated_json=? AND ("+guard+")").bind(item.new,item.resource,item.locale,item.old,...guardArgs));
 }
 const results=await db.batch(statements);
 const counts=results.map(row=>Number(row?.meta?.changes??-1));
 if(counts.some(value=>value!==1))throw Error("Guarded Blog source repair did not update exactly one row per statement: "+JSON.stringify(counts));
 return {success:true,sourceRepair:true,changed:changes.length,states};
}

