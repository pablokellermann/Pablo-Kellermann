from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
import numpy as np, os, sys

UP = "/root/.claude/uploads/1f883b76-be36-50bf-a705-d2154bf0eb3d/"
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
W, H = 1080, int(os.environ.get("ALTURA", 1350))
STORY = H > 1500
TOP = 230 if STORY else 64      # área segura do topo nos Stories
BOT = 230 if STORY else 0       # área segura da base nos Stories
NAVY = (6, 30, 68)
GOLD = (222, 184, 108)
WHITE = (255, 255, 255)

SERIF_B = "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf"
SERIF_I = "/usr/share/fonts/truetype/crosextra/Caladea-Italic.ttf"
SANS = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
SANS_M = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
SANS_B = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
F = lambda p, s: ImageFont.truetype(p, s)

# ---------- logo (versão branca + dourado para fundo escuro) ----------
_l = Image.open(UP + "4bc9be38-image.png").convert("RGBA")
logo = Image.new("RGBA", _l.size, (255, 255, 255, 255)); logo.alpha_composite(_l); logo = logo.convert("RGB")
a = np.asarray(logo).astype(np.float32)
mn = a.min(axis=2)
alpha = np.clip((255 - mn) * 1.7, 0, 255)
gold_mask = (a[..., 0] > a[..., 2] + 45) & (a[..., 0] > 150)
rgb = np.empty_like(a)
rgb[:] = 255
rgb[gold_mask] = a[gold_mask]
logo_w = Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")
logo_w = logo_w.crop(logo_w.getbbox())
mono = logo_w.crop((0, 0, logo_w.width, int(logo_w.height * 0.50)))
mono = mono.crop(mono.getbbox())


def enhance(img):
    img = ImageOps.exif_transpose(img).convert("RGB")
    img = ImageOps.autocontrast(img, cutoff=0.4)
    img = ImageEnhance.Contrast(img).enhance(1.07)
    img = ImageEnhance.Color(img).enhance(1.06)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
    return img


def cover(img, fx=0.5, fy=0.5, zoom=1.0):
    r = max(W / img.width, H / img.height) * zoom
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x = int(np.clip(fx * img.width - W / 2, 0, img.width - W))
    y = int(np.clip(fy * img.height - H / 2, 0, img.height - H))
    return img.crop((x, y, x + W, y + H))


def gradient(base, start, end_alpha=238, top=True):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = np.zeros((H, W, 4), np.uint8)
    px[..., :3] = NAVY
    ys = np.arange(H)
    start = start + (H - 1350) - BOT
    t = np.clip((ys - start) / (H - start), 0, 1) ** 0.85
    al = (t * end_alpha)
    if top:  # leve escurecimento no topo para tag e logo
        al = np.maximum(al, np.clip((TOP + 220 - ys) / 220, 0, 1) ** 1.4 * 165)
    px[..., 3] = al[:, None].astype(np.uint8)
    ov = Image.fromarray(px, "RGBA")
    # vinheta suave
    vy, vx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((vx - W / 2) / (W / 2)) ** 2 + ((vy - H / 2) / (H / 2)) ** 2)
    vg = np.zeros((H, W, 4), np.uint8)
    vg[..., 3] = (np.clip(d - 0.75, 0, 1) * 110).astype(np.uint8)
    base = base.convert("RGBA")
    base.alpha_composite(Image.fromarray(vg, "RGBA"))
    base.alpha_composite(ov)
    return base


def wrap(draw, text, font, maxw):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for w in para.split():
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=font) <= maxw:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def spaced(draw, xy, text, font, fill, sp=4):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + sp
    return x


def dots(draw, idx, total):
    r, gap = 6, 22
    x0 = W / 2 - (total - 1) * gap / 2
    for i in range(total):
        c = GOLD if i == idx else (255, 255, 255, 110)
        rr = r if i == idx else 4
        draw.ellipse((x0 + i * gap - rr, H - 52 - BOT - rr, x0 + i * gap + rr, H - 52 - BOT + rr), fill=c)


M = 72  # margem lateral
TOTAL = 12


def slide(n, photo, fx, fy, tag, title, body, ref, zoom=1.0, gstart=520):
    img = cover(enhance(Image.open(UP + photo)), fx, fy, zoom)
    img = gradient(img, gstart)
    d = ImageDraw.Draw(img)
    # topo: etapa + monograma
    spaced(d, (M, TOP), tag, F(SANS_B, 24), GOLD, 5)
    lg = mono.copy(); lg.thumbnail((200, 74), Image.LANCZOS)
    img.alpha_composite(lg, (W - M - lg.width, TOP - 14))
    # bloco inferior (de baixo para cima)
    ft, fb, fr = F(SERIF_B, 70), F(SANS, 33), F(SANS_M, 24)
    maxw = W - 2 * M
    tl = wrap(d, title, ft, maxw)
    bl = wrap(d, body, fb, maxw)
    rl = wrap(d, ref, fr, maxw - 28) if ref else []
    h_t, h_b, h_r = 78, 46, 34
    total_h = len(tl) * h_t + 30 + 26 + len(bl) * h_b + (30 + len(rl) * h_r if rl else 0)
    y = H - 100 - BOT - total_h
    for l in tl:
        d.text((M, y), l, font=ft, fill=WHITE); y += h_t
    y += 18
    d.rectangle((M, y, M + 90, y + 4), fill=GOLD); y += 38
    for l in bl:
        d.text((M, y), l, font=fb, fill=(240, 243, 248)); y += h_b
    if rl:
        y += 26
        d.rectangle((M, y + 4, M + 4, y + len(rl) * h_r - 6), fill=GOLD)
        for l in rl:
            d.text((M + 22, y), l, font=fr, fill=GOLD); y += h_r
    dots(d, n - 1, TOTAL)
    if n < TOTAL:
        d.text((W - M, H - 52 - BOT), "arraste  →", font=F(SANS_M, 22), fill=(255, 255, 255, 190), anchor="rm")
    img.convert("RGB").save(f"{OUT}/{n:02d}.jpg", quality=94, subsampling=0)


def cover_slide():
    img = cover(enhance(Image.open(UP + "68244d85-image.jpg")), 0.62, 0.32)
    img = gradient(img, 430, 245, top=False)
    d = ImageDraw.Draw(img)
    lg = logo_w.copy(); lg.thumbnail((330, 210), Image.LANCZOS)
    img.alpha_composite(lg, (M, TOP - 4))
    y = H - 590 - BOT
    spaced(d, (M, y), "GUIA PRÁTICO  ·  DIREITO PENAL", F(SANS_B, 24), GOLD, 5); y += 56
    for l in ["Tribunal", "do Júri"]:
        d.text((M, y), l, font=F(SERIF_B, 118), fill=WHITE); y += 118
    y += 22
    d.rectangle((M, y, M + 90, y + 4), fill=GOLD); y += 34
    for l in wrap(d, "Do inquérito policial à sustentação oral no Tribunal de Justiça — passo a passo.", F(SERIF_I, 40), W - 2 * M - 60):
        d.text((M, y), l, font=F(SERIF_I, 40), fill=(240, 243, 248)); y += 50
    dots(d, 0, TOTAL)
    d.text((W - M, H - 52 - BOT), "arraste  →", font=F(SANS_M, 22), fill=(255, 255, 255, 190), anchor="rm")
    img.convert("RGB").save(f"{OUT}/01.jpg", quality=94, subsampling=0)


def final_slide():
    img = cover(enhance(Image.open(UP + "6be1c5b7-image.jpg")), 0.5, 0.38)
    img = gradient(img, 380, 250, top=False)
    d = ImageDraw.Draw(img)
    y = H - 650 - BOT
    for l in wrap(d, "Cada fase é uma oportunidade de defesa.", F(SERIF_B, 66), W - 2 * M):
        d.text((W / 2, y), l, font=F(SERIF_B, 66), fill=WHITE, anchor="ma"); y += 76
    y += 14
    d.rectangle((W / 2 - 45, y, W / 2 + 45, y + 4), fill=GOLD); y += 32
    for l in wrap(d, "A atuação técnica desde o inquérito pode definir o resultado no plenário e no Tribunal.", F(SANS, 31), W - 2 * M - 40):
        d.text((W / 2, y), l, font=F(SANS, 31), fill=(240, 243, 248), anchor="ma"); y += 44
    lg = logo_w.copy(); lg.thumbnail((280, 170), Image.LANCZOS)
    img.alpha_composite(lg, (int(W / 2 - lg.width / 2), y + 34))
    dots(d, TOTAL - 1, TOTAL)
    img.convert("RGB").save(f"{OUT}/{TOTAL:02d}.jpg", quality=94, subsampling=0)


cover_slide()
slide(2, "6c8a2f56-image.jpg", 0.62, 0.38, "ETAPA 01",
      "Inquérito Policial",
      "A Polícia Judiciária investiga autoria e materialidade do crime doloso contra a vida. A defesa já atua: acompanha depoimentos, analisa provas e requer diligências.",
      "Prazo: 10 dias (preso) ou 30 dias (solto) — art. 10, CPP · Diligências — art. 14, CPP")
slide(3, "c2801a26-image.jpg", 0.5, 0.3, "ETAPA 02",
      "Denúncia e Resposta à Acusação",
      "O Ministério Público oferece a denúncia. Recebida, o acusado é citado e apresenta resposta escrita, com preliminares, documentos e até 8 testemunhas.",
      "Art. 406, CPP — prazo de 10 dias")
slide(4, "494f09ef-image.jpg", 0.45, 0.4, "ETAPA 03",
      "Audiência de Instrução",
      "Ouvem-se o ofendido, as testemunhas de acusação e de defesa e os peritos. Por último, o interrogatório do acusado e os debates orais.",
      "Arts. 411 e 412, CPP — procedimento concluído em até 90 dias")
slide(5, "8ab014a2-image.jpg", 0.55, 0.42, "ETAPA 04 · FIM DA 1ª FASE",
      "Decisão do Juiz",
      "Pronúncia: o réu vai a Júri popular.\nImpronúncia: provas insuficientes.\nAbsolvição sumária: hipóteses legais.\nDesclassificação: não é crime doloso contra a vida.",
      "Arts. 413, 414, 415 e 419, CPP · Contra a pronúncia cabe RESE (art. 581, IV)")
slide(6, "6e9ab137-image.jpg", 0.5, 0.36, "ETAPA 05",
      "Preparação para o Plenário",
      "As partes indicam até 5 testemunhas para o plenário, juntam documentos e requerem diligências. É o momento de estudar cada folha do processo.",
      "Art. 422, CPP — 5 dias · Documentos: 3 dias úteis antes da sessão (art. 479)")
slide(7, "a59164ec-image.jpg", 0.42, 0.33, "ETAPA 06",
      "Sessão Plenária",
      "Instalada a sessão, sorteiam-se 7 jurados para o Conselho de Sentença. Cada parte pode recusar até 3 sem justificar. Segue a instrução em plenário.",
      "Arts. 447, 463 e 468, CPP")
slide(8, "c02ee89d-image.jpg", 0.6, 0.33, "ETAPA 07",
      "Debates Orais",
      "Acusação e defesa têm 1h30 cada para sustentar suas teses aos jurados. Réplica e tréplica: 1h cada. Aqui se exerce a plenitude de defesa.",
      "Art. 477, CPP · Art. 5º, XXXVIII, \"a\", CF")
slide(9, "24f710a4-image.jpg", 0.55, 0.33, "ETAPA 08",
      "Quesitos e Veredicto",
      "Em votação sigilosa, os jurados respondem sobre materialidade, autoria e se o acusado deve ser absolvido. O juiz-presidente profere a sentença.",
      "Arts. 483 e 492, CPP · Sigilo e soberania dos veredictos — art. 5º, XXXVIII, \"b\" e \"c\", CF")
slide(10, "1c86be48-image.jpg", 1.0, 0.3, "ETAPA 09",
      "Apelação",
      "Recurso de fundamentação vinculada: nulidade posterior à pronúncia, sentença contrária à lei ou aos jurados, erro na pena ou decisão manifestamente contrária à prova dos autos.",
      "Art. 593, III, CPP — 5 dias para interpor · 8 dias para as razões (art. 600)",
      zoom=1.24)
slide(11, "4aeb2998-image.jpg", 0.4, 0.55, "ETAPA 10",
      "Sustentação Oral no TJ",
      "Na sessão da Câmara Criminal, o advogado vai à tribuna e expõe aos desembargadores os pontos decisivos do recurso, antes do voto.",
      "Decisão manifestamente contrária à prova: provido o recurso, novo Júri — art. 593, § 3º, CPP",
      gstart=470)
final_slide()
print("ok")
