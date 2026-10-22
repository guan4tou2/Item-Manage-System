# 標籤 PDF 字型

`NotoSansTC-Regular.ttf` 為 **Noto Sans TC** 的靜態子集，供伺服器端標籤 PDF 內嵌使用
（reportlab 的 CID 字型不嵌入字型檔，實測部分 PDF 檢視器／印表機會缺繁中字形）。

- 來源：<https://github.com/google/fonts/blob/main/ofl/notosanstc/NotoSansTC%5Bwght%5D.ttf>
- 授權：SIL Open Font License 1.1（見 `OFL.txt`）
- 處理：
  - 以 `fontTools.varLib.instancer` 固定 `wght=400`
  - 保留字型全部 cmap 字元（20,745 個，含繁中、簡中、日文假名與拉丁）
  - 移除 `GSUB`／`GPOS`／`GDEF`／`BASE`／`JSTF`／`MATH`／`SVG` 等 reportlab 不需要的表
    （本專案不做複雜文字排版）
- 產出大小約 6.6 MB；PDF 只嵌入實際用到的字形子集（單張標籤 PDF 約 20 KB）

重新產生（需 `fonttools`，僅開發時使用）：

```bash
uv pip install fonttools
python - <<'PY'
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

font = TTFont("NotoSansTC[wght].ttf")
font = instantiateVariableFont(font, {"wght": 400}, inplace=True)
opts = subset.Options()
opts.layout_features = []
opts.name_IDs = ["*"]
opts.name_legacy = True
opts.notdef_outline = True
opts.recalc_bounds = True
opts.drop_tables += ["DSIG", "GSUB", "GPOS", "GDEF", "BASE", "JSTF", "MATH", "SVG "]
sub = subset.Subsetter(options=opts)
sub.populate(unicodes=sorted(font.getBestCmap()))
sub.subset(font)
font.save("NotoSansTC-Regular.ttf")
PY
```
