import pandas as pd, numpy as np, re, matplotlib.pyplot as plt

excel_path = "Assignment.xlsx"  # update if path differs

def to_number(x):
    if pd.isna(x): return np.nan
    if isinstance(x, (int, float)): return float(x)
    s = str(x)
    s = s.replace(',', '')
    m = re.findall(r'[\d.]+', s)
    if not m: return np.nan
    try:
        return float(m[0])
    except:
        return np.nan

def parse_resolution(val):
    if pd.isna(val): return np.nan
    s = str(val).lower().replace(' ', '')
    m = re.search(r'(\d{3,4})p', s)
    if m: return float(m.group(1))
    if '8k' in s: return 4320.0
    if '5k' in s: return 2880.0
    if '4k' in s or '2160p' in s: return 2160.0
    if '2k' in s or '1440p' in s: return 1440.0
    mp = re.search(r'(\d+(\.\d+)?)\s*mp', s)
    if mp:
        mp_val = float(mp.group(1))
        if mp_val < 1.5: return 720.0
        if mp_val < 3.1: return 1080.0
        if mp_val < 6.1: return 1440.0
        return 2160.0
    return to_number(s)

def parse_distance_meters(val):
    if pd.isna(val): return np.nan
    s = str(val).lower()
    m = re.search(r'([\d.]+)\s*m', s)
    if m: return float(m.group(1))
    f = re.search(r'([\d.]+)\s*(ft|feet|foot|\\\')', s)
    if f: return float(f.group(1)) * 0.3048
    num = to_number(s)
    return num

# def parse_ip_rating(val):
#     if pd.isna(val): return np.nan
#     s = str(val).upper()
#     m = re.search(r'IP\\s*([0-9]{2})', s)
#     if m: return float(m.group(1))
#     d = re.search(r'\\b([0-9]{2})\\b', s)
#     return float(d.group(1)) if d else np.nan

def normalize(series):
    import numpy as np, pandas as pd
    s = series.astype(float)
    s = s.replace([np.inf, -np.inf], np.nan)
    if s.notna().sum() == 0:
        return pd.Series(np.nan, index=s.index)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series(1.0, index=s.index)
    return (s - mn) / (mx - mn)

def find_col(df, keyword_patterns, exclude_patterns=None):
    cols = []
    for c in df.columns:
        lc = c.lower()
        if any(re.search(p, lc) for p in keyword_patterns):
            if not exclude_patterns or not any(re.search(p, lc) for p in exclude_patterns):
                cols.append(c)
    return cols

def main():
    xl = pd.ExcelFile(excel_path)
    df = xl.parse(xl.sheet_names[0])
    df.columns = [str(c).strip() for c in df.columns]
    lower_map = {c: re.sub(r'\\s+', '_', str(c).strip().lower()) for c in df.columns}
    df.rename(columns=lower_map, inplace=True)

    name_cols = find_col(df, [r'name', r'model', r'title'])
    resolution_cols = find_col(df, [r'resolution', r'\\bmp\\b', r'4k', r'1080p', r'720p', r'pixels'])
    night_cols = find_col(df, [r'night', r'ir', r'infrared', r'vision'])
    durability_cols = find_col(df, [r'ip\\d{2}', r'\\bip\\b', r'water', r'weather', r'durab'])
    price_cols = find_col(df, [r'price', r'cost', r'amount'])
    amazon_cols = find_col(df, [r'amazon'])
    flipkart_cols = find_col(df, [r'flipkart'])
    rating_cols = find_col(df, [r'rating', r'review'], exclude_patterns=[r'count'])

    name_col = name_cols[0] if name_cols else (find_col(df, [r'name|title|model'])[0] if find_col(df, [r'name|title|model']) else df.columns[0])
    resolution_col = resolution_cols[0] if resolution_cols else None
    night_col = night_cols[0] if night_cols else None
    durability_col = durability_cols[0] if durability_cols else None
    rating_col = rating_cols[0] if rating_cols else None

    amazon_price_col = None
    for c in amazon_cols:
        if c in price_cols: amazon_price_col = c; break
    if not amazon_price_col:
        for c in price_cols:
            if 'amazon' in c: amazon_price_col = c; break

    flipkart_price_col = None
    for c in flipkart_cols:
        if c in price_cols: flipkart_price_col = c; break
    if not flipkart_price_col:
        for c in price_cols:
            if 'flipkart' in c: flipkart_price_col = c; break

    general_price_col = None
    if not (amazon_price_col or flipkart_price_col):
        for c in price_cols:
            if re.search(r'\\bprice\\b', c.lower()):
                general_price_col = c; break
        if general_price_col is None and price_cols:
            general_price_col = price_cols[0]

    df_feat = df.copy()
    if resolution_col:
        df_feat['resolution_p'] = df_feat[resolution_col].apply(parse_resolution)
    if night_col:
        df_feat['night_range_m'] = df_feat[night_col].apply(parse_distance_meters)
    # if durability_col:
    #     df_feat['ip_rating_num'] = df_feat[durability_col].apply(parse_ip_rating)

    if amazon_price_col:
        df_feat['price_amazon'] = df_feat[amazon_price_col].apply(to_number)
    if flipkart_price_col:
        df_feat['price_flipkart'] = df_feat[flipkart_price_col].apply(to_number)
    if general_price_col:
        df_feat['price_general'] = df_feat[general_price_col].apply(to_number)

    price_series_list = [s for s in [df_feat.get('price_amazon'), df_feat.get('price_flipkart'), df_feat.get('price_general')] if s is not None]
    if price_series_list:
        df_feat['price_avg'] = pd.concat(price_series_list, axis=1).mean(axis=1, skipna=True)

    if rating_col:
        df_feat['rating_num'] = df_feat[rating_col].apply(to_number)

    present_feats = {}
    if 'resolution_p' in df_feat and df_feat['resolution_p'].notna().sum() > 0:
        df_feat['res_norm'] = normalize(df_feat['resolution_p']); present_feats['res_norm'] = 0.30
    if 'night_range_m' in df_feat and df_feat['night_range_m'].notna().sum() > 0:
        df_feat['night_norm'] = normalize(df_feat['night_range_m']); present_feats['night_norm'] = 0.25
    # if 'ip_rating_num' in df_feat and df_feat['ip_rating_num'].notna().sum() > 0:
    #     df_feat['ip_norm'] = normalize(df_feat['ip_rating_num']); present_feats['ip_norm'] = 0.20
    if 'price_avg' in df_feat and df_feat['price_avg'].notna().sum() > 0:
        df_feat['price_norm'] = normalize(df_feat['price_avg']); present_feats['price_norm_inv'] = 0.15
    if 'rating_num' in df_feat and df_feat['rating_num'].notna().sum() > 0:
        df_feat['rating_norm'] = normalize(df_feat['rating_num']); present_feats['rating_norm'] = 0.10

    total_w = sum(present_feats.values()) if present_feats else 1.0
    weights = {k: v/total_w for k, v in present_feats.items()}

    score = pd.Series(0.0, index=df_feat.index)
    for k, w in weights.items():
        if k == 'price_norm_inv' and 'price_norm' in df_feat:
            comp = 1 - df_feat['price_norm']
            score += w * comp.fillna(comp.mean())
        else:
            comp = df_feat.get(k, pd.Series(np.nan, index=df_feat.index))
            score += w * comp.fillna(comp.mean())
    df_feat['score'] = score

    id_col = name_col if name_col in df_feat.columns else df_feat.columns[0]

    display_cols = [id_col]
    for c in ['score','price_avg','resolution_p','night_range_m','rating_num']:
        if c in df_feat.columns:
            display_cols.append(c)
    df_top10 = df_feat.sort_values('score', ascending=False).head(10)[display_cols].reset_index(drop=True)
    df_top10.to_excel("Top10_CCTV.xlsx", index=False)

    plt.figure()
    plt.bar(df_top10[id_col].astype(str), df_top10['score'])
    plt.xticks(rotation=45, ha='right')
    plt.title("Top 10 CCTV Cameras - Composite Score")
    plt.tight_layout()
    plt.savefig("top10_scores.png")
    plt.close()

if __name__ == "__main__":
    main()
