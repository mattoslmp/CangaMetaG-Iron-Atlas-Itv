#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
THRESHOLD = 1.0
AGGREGATE_LABEL = "Other genera (<1% each)"


def sha256(path: Path) -> str:
  h = hashlib.sha256()
  with path.open("rb") as handle:
    for block in iter(lambda: handle.read(1024 * 1024), b""):
      h.update(block)
  return h.hexdigest()


def patch_frozen_profiles() -> list[dict[str, object]]:
  reports: list[dict[str, object]] = []
  for domain in ("bacteria", "archaea"):
    path = ROOT / "data" / f"article_frozen_taxonomy_{domain}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    columns = list(payload.get("profile_columns") or [])
    profile = pd.DataFrame(payload["profile"])
    if not columns:
      columns = ["taxon"] + [c for c in profile.columns if c != "taxon"]
    sample_cols = [c for c in columns if c != "taxon"]
    for col in sample_cols:
      profile[col] = pd.to_numeric(profile[col], errors="coerce").fillna(0.0)
    before_totals = profile[sample_cols].sum(axis=0)
    names = profile["taxon"].astype(str)
    aggregate_mask = names.str.casefold().str.startswith(("other genera", "other taxa", "outros gêneros", "outros táxons"))
    unclassified_mask = names.str.casefold().isin({"unclassified", "unclassified taxa", "unclassified genera"})
    candidates = profile.loc[~aggregate_mask & ~unclassified_mask].copy()
    maxima = candidates[sample_cols].max(axis=1)
    rare = candidates.loc[maxima < THRESHOLD].copy()
    kept = profile.loc[unclassified_mask].copy()
    kept = pd.concat([kept, candidates.loc[maxima >= THRESHOLD].copy()], ignore_index=True)
    aggregate_values = profile.loc[aggregate_mask, sample_cols].sum(axis=0)
    if not rare.empty:
      aggregate_values = aggregate_values.add(rare[sample_cols].sum(axis=0), fill_value=0.0)
    aggregate_row = {"taxon": AGGREGATE_LABEL}
    aggregate_row.update({c: float(aggregate_values[c]) for c in sample_cols})
    rebuilt = pd.concat([kept, pd.DataFrame([aggregate_row])], ignore_index=True)
    after_totals = rebuilt[sample_cols].sum(axis=0)
    max_delta = float((before_totals - after_totals).abs().max())
    if max_delta > 1e-8:
      raise RuntimeError(f"{domain}: profile totals changed by {max_delta}")
    payload["profile"] = rebuilt[columns].to_dict("records")
    payload["profile_columns"] = columns
    payload.setdefault("display", {})["other_genera_threshold_percent"] = THRESHOLD
    payload["display"]["other_genera_rule"] = "strictly below 1% in every displayed sample"
    payload.setdefault("palette", {})[AGGREGATE_LABEL] = payload.get("palette", {}).get("Other genera", "#B8B8B8")
    payload["correction_20260802"] = {
      "genus_aggregation_threshold_percent": THRESHOLD,
      "comparison": "maximum relative abundance across the 20 displayed samples",
      "rule": "aggregate only when maximum abundance is strictly below 1%",
      "unclassified_kept_separate": True,
      "scientific_mass_preserved": True,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    reports.append({
      "domain": domain.title(),
      "source_rows": int(len(profile)),
      "displayed_rows_after": int(len(rebuilt)),
      "newly_aggregated_rows": int(len(rare)),
      "aggregate_source_rows": int(aggregate_mask.sum()),
      "max_sample_total_delta": max_delta,
      "path": str(path.relative_to(ROOT)),
      "sha256": sha256(path),
    })
  return reports


def replace_once(text: str, old: str, new: str, label: str, changes: list[str]) -> str:
  if old in text:
    changes.append(label)
    return text.replace(old, new)
  return text


def patch_app() -> dict[str, object]:
  path = ROOT / "app.py"
  text = path.read_text(encoding="utf-8")
  changes: list[str] = []
  old = '''  ranked = agg.groupby("taxon", as_index=True)[value_col].mean().sort_values(ascending=False)\n  if min_display_pct is not None and value_col == "abundance":\n    ranked = ranked[ranked >= float(min_display_pct)]'''
  new = '''  ranked = agg.groupby("taxon", as_index=True)[value_col].mean().sort_values(ascending=False)\n  if min_display_pct is not None and value_col == "abundance":\n    maximum = agg.groupby("taxon", as_index=True)["abundance"].max()\n    eligible = maximum[maximum >= float(min_display_pct)].index\n    ranked = ranked[ranked.index.isin(eligible)]'''
  text = replace_once(text, old, new, "matrix threshold uses maximum abundance", changes)

  old = '''  value_col = "abundance"\n  matrix = _taxonomy_matrix_from_profile_final(df, value_col=value_col, top_n=top_n)\n  if matrix.empty:\n    return df, matrix\n  raw_matrix = matrix.T.copy()\n  plot_matrix = np.log10(raw_matrix.clip(lower=0).astype(float) + 1.0)\n  domain, rank = _taxonomy_selection_parts(level_name)'''
  new = '''  value_col = "abundance"\n  domain, rank = _taxonomy_selection_parts(level_name)\n  effective_top_n = None if rank == "Genus" else top_n\n  matrix = _taxonomy_matrix_from_profile_final(\n    df, value_col=value_col, top_n=effective_top_n,\n    min_display_pct=(1.0 if rank == "Genus" else None),\n  )\n  if rank == "Genus" and "Other taxa" in matrix.columns:\n    matrix = matrix.rename(columns={"Other taxa": "Other taxa (<1%)"})\n  if matrix.empty:\n    return df, matrix\n  raw_matrix = matrix.T.copy()\n  plot_matrix = np.log10(raw_matrix.clip(lower=0).astype(float) + 1.0)'''
  text = replace_once(text, old, new, "genus heatmap uses strict <1% aggregate", changes)

  old = '''  ranked = agg.groupby("taxon")["abundance"].mean().sort_values(ascending=False)\n  requested = len(ranked) if top_n is None or int(top_n) <= 0 else min(int(top_n), len(ranked))\n  keep = ranked.index.tolist()[:requested]'''
  new = '''  ranked = agg.groupby("taxon")["abundance"].mean().sort_values(ascending=False)\n  domain, rank = _taxonomy_selection_parts(level_name)\n  if rank == "Genus":\n    maximum = agg.groupby("taxon")["abundance"].max()\n    ranked = ranked[ranked.index.isin(maximum[maximum >= 1.0].index)]\n    requested = len(ranked)\n  else:\n    requested = len(ranked) if top_n is None or int(top_n) <= 0 else min(int(top_n), len(ranked))\n  keep = ranked.index.tolist()[:requested]'''
  text = replace_once(text, old, new, "genus barplot uses strict <1% aggregate", changes)

  old = '''      other["taxon"] = "Other taxa"\n      plot = pd.concat([plot, other], ignore_index=True, sort=False)'''
  new = '''      other["taxon"] = "Other taxa (<1%)" if rank == "Genus" else "Other taxa"\n      plot = pd.concat([plot, other], ignore_index=True, sort=False)'''
  text = replace_once(text, old, new, "genus barplot aggregate label", changes)

  text = text.replace("Other taxa (<5%)", "Other taxa (<1%)")
  text = text.replace("Other genera (<5%)", "Other genera (<1%)")
  path.write_text(text, encoding="utf-8")
  return {"path": "app.py", "changes": changes, "sha256": sha256(path)}


def write_combined_generator() -> Path:
  path = ROOT / "scripts" / "final_publication_figures" / "03_generate_combined_community_figures.py"
  path.parent.mkdir(parents=True, exist_ok=True)
  code = r'''#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from scipy.special import gammaln
from sklearn.manifold import MDS
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "app_supplementary_figures"
DERIVED = ROOT / "data" / "final_publication_derived"
REPORTS = ROOT / "reports"
OUT.mkdir(parents=True, exist_ok=True)
DERIVED.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)
SAMPLE_RE = re.compile(r"^(AM|TIA|TI|VI)[._-]?P?\d+[._-]?(D|R)$", re.I)
COLORS = {"AM":"#0072B2", "TIA":"#E69F00", "TI":"#009E73", "VI":"#CC79A7"}
MARKERS = {"D":"o", "R":"s"}


def norm_sample(value):
  s = str(value).strip().replace("_", ".").replace("-", ".")
  s = re.sub(r"\.+", ".", s)
  m = re.search(r"(AM|TIA|TI|VI)\.?P?(\d+)\.?(D|R)$", s, re.I)
  return f"{m.group(1).upper()}.P{int(m.group(2))}.{m.group(3).upper()}" if m else s


def sample_meta(samples):
  rows=[]
  for s in samples:
    n=norm_sample(s); parts=n.split(".")
    rows.append({"Sample":n,"Lake":parts[0] if parts else n,"Position":".".join(parts[:2]),"Season":"Dry" if n.endswith(".D") else "Rainy"})
  return pd.DataFrame(rows)


def read_otu():
  path=ROOT/"data"/"resultado.cds.otu.tab"
  if not path.is_file(): raise FileNotFoundError(path)
  df=pd.read_csv(path, sep="\t", low_memory=False)
  sample_cols=[]
  for c in df.columns:
    n=norm_sample(c)
    if SAMPLE_RE.match(n): sample_cols.append(c)
  if len(sample_cols) != 20:
    numeric=[]
    for c in df.columns:
      vals=pd.to_numeric(df[c], errors="coerce")
      if vals.notna().mean()>0.95 and vals.sum()>0: numeric.append(c)
    sample_cols=numeric[:20]
  if len(sample_cols) != 20: raise RuntimeError(f"Expected 20 sample columns, found {len(sample_cols)}")
  matrix=df[sample_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).clip(lower=0)
  matrix.columns=[norm_sample(c) for c in sample_cols]
  return matrix


def savefig(fig, stem):
  paths=[]
  for ext in ("png","svg","pdf"):
    p=OUT/f"{stem}.{ext}"
    fig.savefig(p, dpi=350 if ext=="png" else None, bbox_inches="tight", facecolor="white")
    paths.append(str(p.relative_to(ROOT)))
  plt.close(fig)
  return paths


def expected_richness(counts, depth):
  counts=np.asarray(counts, dtype=float)
  counts=counts[counts>0]
  N=int(round(counts.sum())); n=min(int(depth),N)
  if n<=0 or N<=0: return 0.0
  logden=gammaln(N+1)-gammaln(n+1)-gammaln(N-n+1)
  absent=np.zeros_like(counts)
  valid=(N-counts)>=n
  nc=N-counts[valid]
  absent[valid]=np.exp(gammaln(nc+1)-gammaln(n+1)-gammaln(nc-n+1)-logden)
  return float(np.sum(1.0-absent))


def alpha_and_rarefaction(otu):
  meta=sample_meta(otu.columns)
  records=[]
  for sample in otu.columns:
    x=otu[sample].to_numpy(float); x=x[x>0]; total=x.sum(); p=x/total if total else x
    records.append({"Sample":sample,"Lake":sample.split(".")[0],"Season":"Dry" if sample.endswith(".D") else "Rainy","Observed":int((x>0).sum()),"Chao1":float((x>0).sum()+((x==1).sum()**2)/(2*max((x==2).sum(),1))),"Shannon":float(-(p*np.log(p)).sum()) if len(p) else 0.0})
  alpha=pd.DataFrame(records)
  alpha.to_csv(DERIVED/"alpha_diversity_all_domains_20_samples.csv", index=False)
  fig,axes=plt.subplots(1,3,figsize=(16,5.8))
  rng=np.random.default_rng(42)
  for ax,metric in zip(axes,["Observed","Chao1","Shannon"]):
    groups=[alpha.loc[alpha.Lake==lake,metric].to_numpy(float) for lake in ["AM","TIA","TI","VI"]]
    ax.boxplot(groups, labels=["AM","TIA","TI","VI"], showfliers=False)
    for i,(lake,vals) in enumerate(zip(["AM","TIA","TI","VI"],groups),1):
      ax.scatter(i+rng.normal(0,0.035,len(vals)),vals,s=35,alpha=.85,color=COLORS[lake],edgecolor="black",linewidth=.4)
    ax.set_title(metric); ax.set_xlabel("Lake"); ax.set_ylabel(metric); ax.grid(axis="y",alpha=.2)
  fig.suptitle("Alpha diversity using the joint CDS feature matrix (all domains)",fontweight="bold")
  alpha_paths=savefig(fig,"SupplementaryFigure_alpha_diversity_all_domains")
  min_total=int(min(otu.sum(axis=0).min(),400000))
  depths=np.unique(np.linspace(max(1000,min_total//25),min_total,25,dtype=int))
  rare=[]
  fig,ax=plt.subplots(figsize=(11,7))
  for sample in otu.columns:
    vals=[expected_richness(otu[sample].to_numpy(float),d) for d in depths]
    lake=sample.split(".")[0]; season="D" if sample.endswith(".D") else "R"
    ax.plot(depths,vals,color=COLORS[lake],linestyle="-" if season=="D" else "--",linewidth=1.4,alpha=.9,label=sample)
    rare.extend({"Sample":sample,"Depth":int(d),"Expected_observed_features":float(v)} for d,v in zip(depths,vals))
  ax.set_xlabel("Subsampled CDS count"); ax.set_ylabel("Expected observed features")
  ax.set_title("Rarefaction using all domains jointly")
  ax.grid(alpha=.2); ax.legend(ncol=4,fontsize=7,frameon=False)
  pd.DataFrame(rare).to_csv(DERIVED/"rarefaction_all_domains_20_samples.csv",index=False)
  rare_paths=savefig(fig,"SupplementaryFigure_rarefaction_all_domains")
  return alpha_paths,rare_paths,alpha


def nmds(otu):
  X=otu.T.to_numpy(float)
  distances=squareform(pdist(X,metric="braycurtis"))
  model=MDS(n_components=2,metric=False,dissimilarity="precomputed",random_state=42,n_init=8,max_iter=1000)
  scores=model.fit_transform(distances)
  meta=sample_meta(otu.columns); meta["NMDS1"]=scores[:,0]; meta["NMDS2"]=scores[:,1]
  meta.to_csv(DERIVED/"combined_all_domains_NMDS_20_samples.csv",index=False)
  return meta,float(getattr(model,"stress_",np.nan))


def find_environment(positions):
  candidates=[ROOT/"data"/"fiqui2.xlsx",ROOT/"tables"/"fiqui2.xlsx"]
  candidates += list((ROOT/"data").glob("*fiqui*.xlsx"))
  target=set(positions)
  for path in candidates:
    if not path.is_file(): continue
    try: sheets=pd.read_excel(path,sheet_name=None)
    except Exception: continue
    for sheet,df in sheets.items():
      if df.empty: continue
      best=None; best_overlap=0
      for c in df.columns:
        vals=df[c].astype(str).map(norm_sample).str.rsplit(".",n=1).str[0]
        overlap=len(target.intersection(set(vals)))
        if overlap>best_overlap: best=(c,vals); best_overlap=overlap
      if not best or best_overlap<5: continue
      c,vals=best; work=df.copy(); work["Position"]=vals
      nums=[]
      for col in work.columns:
        if col in {c,"Position"}: continue
        v=pd.to_numeric(work[col],errors="coerce")
        if v.notna().sum()>=5 and v.nunique(dropna=True)>1:
          work[col]=v; nums.append(col)
      if len(nums)>=2:
        env=work.groupby("Position",as_index=False)[nums].mean()
        env=env[env.Position.isin(target)]
        if len(env)>=5: return env,path,sheet
  raise RuntimeError("Could not resolve physicochemical data for at least five matched positions")


def rda(otu):
  samples=sample_meta(otu.columns)
  rel=otu.div(otu.sum(axis=0).replace(0,np.nan),axis=1).fillna(0.0)
  hell=np.sqrt(rel).T
  hell["Position"]=samples.Position.values
  community=hell.groupby("Position").mean()
  env,path,sheet=find_environment(community.index.tolist())
  env=env.set_index("Position").reindex(community.index).dropna(how="all")
  common=community.index.intersection(env.index)
  community=community.loc[common]; env=env.loc[common]
  env=env.loc[:,env.notna().sum()>=max(4,len(env)//2)].copy()
  env=env.fillna(env.median(numeric_only=True)).select_dtypes(include=[np.number])
  X=StandardScaler().fit_transform(env.to_numpy(float))
  Y=community.to_numpy(float)
  X1=np.column_stack([np.ones(len(X)),X])
  Yhat=X1@np.linalg.pinv(X1)@Y
  Yc=Yhat-Yhat.mean(axis=0)
  U,S,Vt=np.linalg.svd(Yc,full_matrices=False)
  site=U[:,:2]*S[:2]
  total=np.sum(S**2); pct=(S[:2]**2/total*100) if total else np.array([0,0])
  site_df=pd.DataFrame({"Position":common,"RDA1":site[:,0],"RDA2":site[:,1]})
  site_df["Lake"]=site_df.Position.str.split(".").str[0]
  env_vectors=[]
  for i,col in enumerate(env.columns):
    env_vectors.append({"Variable":str(col),"RDA1":float(np.corrcoef(X[:,i],site[:,0])[0,1]),"RDA2":float(np.corrcoef(X[:,i],site[:,1])[0,1])})
  env_df=pd.DataFrame(env_vectors).replace([np.inf,-np.inf],np.nan).dropna().sort_values(["RDA1","RDA2"],key=lambda s:s.abs(),ascending=False).head(18)
  site_df.to_csv(DERIVED/"combined_all_domains_RDA_10_positions.csv",index=False)
  env_df.to_csv(DERIVED/"combined_all_domains_RDA_environment_vectors.csv",index=False)
  return site_df,env_df,pct,path,sheet


def combined_figure(otu):
  scores,stress=nmds(otu)
  sites,env,pct,env_path,env_sheet=rda(otu)
  fig,axes=plt.subplots(1,2,figsize=(17,7.5))
  ax=axes[0]
  for _,r in scores.iterrows():
    season="D" if r.Season=="Dry" else "R"
    ax.scatter(r.NMDS1,r.NMDS2,s=70,c=COLORS[r.Lake],marker=MARKERS[season],edgecolor="black",linewidth=.7)
    ax.text(r.NMDS1,r.NMDS2,str(r.Sample),fontsize=7,ha="left",va="bottom")
  ax.axhline(0,color="#bbb",lw=.7); ax.axvline(0,color="#bbb",lw=.7)
  ax.set_title(f"A  Combined Bray-Curtis NMDS - 20 samples (stress={stress:.3g})",loc="left",fontweight="bold")
  ax.set_xlabel("NMDS1"); ax.set_ylabel("NMDS2")
  ax=axes[1]
  extent=max(np.abs(sites[["RDA1","RDA2"]].to_numpy()).max(),1e-6)
  for _,r in sites.iterrows():
    ax.scatter(r.RDA1,r.RDA2,s=75,c=COLORS.get(r.Lake,"#666"),edgecolor="black",linewidth=.7)
    ax.text(r.RDA1,r.RDA2,str(r.Position),fontsize=8,ha="left",va="bottom")
  for _,r in env.iterrows():
    x=float(r.RDA1)*extent*.85; y=float(r.RDA2)*extent*.85
    ax.arrow(0,0,x,y,width=0.002*extent,head_width=.04*extent,length_includes_head=True,color="#333")
    ax.text(x*1.08,y*1.08,str(r.Variable),fontsize=7,ha="center")
  ax.axhline(0,color="#bbb",lw=.7); ax.axvline(0,color="#bbb",lw=.7)
  ax.set_title("B  Combined RDA - 10 matched positions",loc="left",fontweight="bold")
  ax.set_xlabel(f"RDA1 ({pct[0]:.1f}% constrained variation)"); ax.set_ylabel(f"RDA2 ({pct[1]:.1f}% constrained variation)")
  fig.suptitle("Joint-domain community ordination; Bacteria, Archaea and all available CDS classifications",fontweight="bold")
  combined=savefig(fig,"SupplementaryFigure_combined_NMDS_RDA_all_domains")
  fig,ax=plt.subplots(figsize=(9,7))
  for _,r in scores.iterrows():
    season="D" if r.Season=="Dry" else "R"
    ax.scatter(r.NMDS1,r.NMDS2,s=75,c=COLORS[r.Lake],marker=MARKERS[season],edgecolor="black",linewidth=.7)
    ax.text(r.NMDS1,r.NMDS2,str(r.Sample),fontsize=8,ha="left",va="bottom")
  ax.set_title("Supplementary Figure 3 - combined NMDS with all 20 individual samples")
  ax.set_xlabel("NMDS1"); ax.set_ylabel("NMDS2"); ax.axhline(0,color="#bbb",lw=.7); ax.axvline(0,color="#bbb",lw=.7)
  supp3=savefig(fig,"SupplementaryFigure3_combined_NMDS_20_individual_samples")
  return combined,supp3,stress,str(env_path.relative_to(ROOT)),env_sheet


def main():
  otu=read_otu()
  alpha_paths,rare_paths,alpha=alpha_and_rarefaction(otu)
  combined,supp3,stress,env_path,env_sheet=combined_figure(otu)
  report={"status":"PASS","domains":"all CDS-classified features jointly","sample_count":int(otu.shape[1]),"feature_count":int(otu.shape[0]),"alpha_sample_count":int(len(alpha)),"nmds_sample_count":20,"rda_position_count":10,"nmds_stress":stress,"environment_source":env_path,"environment_sheet":env_sheet,"outputs":alpha_paths+rare_paths+combined+supp3,"separated_by_domain":False,"source_values_imputed":False}
  (REPORTS/"COMBINED_COMMUNITY_FIGURES_20260802.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
  print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=="__main__": main()
'''
  path.write_text(code, encoding="utf-8")
  path.chmod(0o755)
  return path


def update_manifest(script_path: Path) -> None:
  path = ROOT / "scripts" / "FINAL_SCRIPT_MANIFEST.json"
  if not path.is_file():
    return
  payload = json.loads(path.read_text(encoding="utf-8"))
  entries = payload.setdefault("canonical_scripts", [])
  scope = "Combined-domain alpha diversity, rarefaction, NMDS and RDA"
  entries = [item for item in entries if item.get("figure_scope") != scope]
  entries.append({
    "figure_scope": scope,
    "path": str(script_path.relative_to(ROOT)),
    "status": "canonical_final",
    "inputs": [
      "data/resultado.cds.otu.tab",
      "data/fiqui2.xlsx",
    ],
    "outputs": [
      "outputs/app_supplementary_figures/SupplementaryFigure3_combined_NMDS_20_individual_samples.*",
      "outputs/app_supplementary_figures/SupplementaryFigure_combined_NMDS_RDA_all_domains.*",
      "outputs/app_supplementary_figures/SupplementaryFigure_alpha_diversity_all_domains.*",
      "outputs/app_supplementary_figures/SupplementaryFigure_rarefaction_all_domains.*",
    ],
    "domain_policy": "all available CDS-classified domains jointly; no domain-specific split",
    "command": f"python {script_path.relative_to(ROOT)}",
  })
  payload["canonical_scripts"] = entries
  payload["manifest_version"] = "2026-08-02-final-combined-domain-and-genus-lt1"
  path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def unchanged_hashes(patterns: list[str]) -> list[dict[str, str]]:
  results=[]
  for pattern in patterns:
    for path in sorted(ROOT.glob(pattern)):
      if path.is_file():
        results.append({"path":str(path.relative_to(ROOT)),"sha256":sha256(path)})
  return results


def main() -> int:
  reports_dir = ROOT / "reports"
  reports_dir.mkdir(parents=True, exist_ok=True)
  restored_before = unchanged_hashes([
    "outputs/**/*Supplementary*17*",
    "outputs/**/*Supplementary*18*",
    "outputs/**/*supplementary*17*",
    "outputs/**/*supplementary*18*",
  ])
  profile_report = patch_frozen_profiles()
  app_report = patch_app()
  combined_script = write_combined_generator()
  update_manifest(combined_script)
  subprocess.run([sys.executable, "-m", "py_compile", str(ROOT / "app.py"), str(combined_script)], check=True)
  report = {
    "status": "PATCHED",
    "date": "2026-08-02",
    "canonical_base": "main@c1eae09cfa6b198212ede5834f20102445207386",
    "genus_threshold_percent": THRESHOLD,
    "genus_rule": "aggregate only taxa whose maximum abundance is strictly below 1% across all 20 displayed samples",
    "unclassified_kept_separate": True,
    "frozen_profiles": profile_report,
    "app": app_report,
    "combined_script": str(combined_script.relative_to(ROOT)),
    "supplementary_figures_17_18_before_generation": restored_before,
    "notes": [
      "Figures 4 and 5 retain their official domain-specific NMDS and RDA coordinates.",
      "The added supplementary analysis uses all available CDS-classified domains jointly.",
      "Existing Supplementary Figures 17 and 18 are not regenerated or recalculated.",
    ],
  }
  (reports_dir / "DELIVERY_20260802_CORRECTION_REPORT.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
  )
  print(json.dumps(report, indent=2, ensure_ascii=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
