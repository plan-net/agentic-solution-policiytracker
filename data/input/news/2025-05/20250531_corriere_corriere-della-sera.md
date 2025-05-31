---
title: Corriere della Sera
url: https://www.corriere.it/edicola/index.jsp?path=SPORT&doc=ZIDA
published_date: 2025-05-31T00:00:18.911748
collected_date: 2025-05-31T00:00:18.911840
source: Corriere
source_url: https://www.corriere.it
description: "&lt;%
if (request.getParameter(\"path\") != null) {
String strPath = \"PRIMA_PAGINA\";
String strDoc;
String strXSL;
if (request.getParameter(\"doc\") != null) {
strDoc = \"/edicola/Corsera/\" + strPath + \"/\" + request.getParameter(\"doc\") + \".xml\";
strXSL = \"/edicola/edicola.xsl\";
} else {
strDoc..."
language: en
---

# Corriere della Sera

&lt;%
if (request.getParameter("path") != null) {
String strPath = "PRIMA_PAGINA";
String strDoc;
String strXSL;
if (request.getParameter("doc") != null) {
strDoc = "/edicola/Corsera/" + strPath + "/" + request.getParameter("doc") + ".xml";
strXSL = "/edicola/edicola.xsl";
} else {
strDoc...

&lt;%
if (request.getParameter("path") != null) {
String strPath = "PRIMA_PAGINA";
String strDoc;
String strXSL;
if (request.getParameter("doc") != null) {
strDoc = "/edicola/Corsera/" + strPath + "/" + request.getParameter("doc") + ".xml";
strXSL = "/edicola/edicola.xsl";
} else {
strDoc = "/edicola/Corsera/" + strPath + "/" + "titles.xml";
if (strPath.equals("COMMENTI") || strPath.equals("PRIMA_PAGINA"))
strXSL = "/edicola/" + strPath + "titles.xsl";
else
strXSL = "/edicola/titles.xsl";
}
String strParam = "sezione='" + strPath + "'";
%&gt;
&lt;% } %&gt;
 
 &lt;%@ include file="/tools/includes/ads/edi_300x600.inc" %&gt; 
 
 &lt;%@ include file="/edicola/index_bottom.shtml" %&gt;