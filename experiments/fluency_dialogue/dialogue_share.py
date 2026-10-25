import sys,json,random; S='/tmp/claude-0/-home-claude/742bf5f4-9d1d-5dbf-adac-ab4998fbfd0a/scratchpad/'
sys.path.insert(0,S+'r2'); sys.path.insert(0,S+'repo/sinhala-story-eval/src')
from load import load; from sinhala_story_eval.segment import segment, dialogue_spans
import pandas as pd, numpy as np
from scipy.stats import pearsonr, spearmanr
import statsmodels.api as sm
R=S+'repo/sinhala-story-eval/'
g=json.load(open(R+'data/stories/generated30_stories.json',encoding='utf-8'))
full=pd.read_csv('/root/.claude/uploads/742bf5f4-9d1d-5dbf-adac-ab4998fbfd0a/da552cb2-all38_full_scores.csv',encoding='utf-8-sig')
pool=[(s['id'],s['model']) for s in g]; random.Random(42).shuffle(pool)
key=pd.DataFrame([(f'S{i:02d}',a,b) for i,(a,b) in enumerate(pool,1)],columns=['blind','id','model'])
r,dims=load()
h=r[r.rater.isin(['R1','R2','R3','R5'])].groupby('story')['Fluency'].mean().rename('flu')
txt={(s['id'],s['model']):s['text'] for s in g}
rows=[]
for (i,m),t in txt.items():
    n,d=segment(t); nw,dw=len(n.split()),len(d.split()); nc,dc=len(n),len(d)
    rows.append(dict(id=i,model=m,share_w=dw/(nw+dw),share_c=dc/(nc+dc),spans=len([x for x in dialogue_spans(t) if x.strip()])))
x=key.merge(pd.DataFrame(rows),on=['id','model']).merge(full,on=['id','model']).set_index('blind').join(h)
def partial(y,a,cov):
    Z=sm.add_constant(x[cov]); ry=sm.OLS(x[y],Z).fit().resid; ra=sm.OLS(x[a],Z).fit().resid; return pearsonr(ry,ra)
out=[]
P=lambda s: out.append(s) or print(s)
P(f"n={len(x)}")
P(f"check: whole r={pearsonr(x.pppl_overall,x.flu)[0]:+.3f}; partial|spans(dia_lines) r={partial('flu','pppl_overall',['dia_lines'])[0]:+.3f}; partial|spans(recount) r={partial('flu','pppl_overall',['spans'])[0]:+.3f}")
P(f"dialogue share (words) mean={x.share_w.mean():.3f} range {x.share_w.min():.3f}-{x.share_w.max():.3f}")
for c in ['share_w','share_c','ratio']:
    a=pearsonr(x[c],x.pppl_overall); b=pearsonr(x[c],x.flu); pr=partial('flu','pppl_overall',[c])
    P(f"{c}: r(share,PPPL)={a[0]:+.3f} (p={a[1]:.3g}); r(share,fluency)={b[0]:+.3f} (p={b[1]:.3g}); partial r(PPPL,fluency | {c})={pr[0]:+.3f} (p={pr[1]:.3f})")
pr=partial('flu','pppl_overall',['share_w','dia_lines']); P(f"partial | share_w + spans: r={pr[0]:+.3f} (p={pr[1]:.3f})")
x['lnar']=np.log(x.pppl_narrative); x['ldia']=np.log(x.pppl_dialogue)
f=sm.OLS(x.flu,sm.add_constant(x[['lnar','ldia','share_w']])).fit()
P("regression flu ~ log nar PPPL + log dia PPPL + share_w:")
for k in f.params.index: P(f"  {k}: b={f.params[k]:+.3f} p={f.pvalues[k]:.3f}")
P(f"  R2={f.rsquared:.3f}")
# within-model partial
for m in ['gemini','deepseek','gpt']:
    s=x[x.model==m]; P(f"{m}: share_w mean={s.share_w.mean():.3f} PPPL mean={s.pppl_overall.mean():.2f}")
d=pd.get_dummies(x.model,drop_first=True).astype(float); x=x.join(d)
pr=partial('flu','pppl_overall',['share_w']+list(d.columns)); P(f"partial | share_w + model: r={pr[0]:+.3f} (p={pr[1]:.3f})")
open('dialogue_share_summary.txt','w').write("F3 analysis (25 Oct 2026). Four-rater fluency means (R4 excluded). Dialogue share = words inside quoted spans / all words (segment.py v4).\n\n"+"\n".join(out)+"\n")
x=x
a=pearsonr(x.spans,x.pppl_overall); b=pearsonr(x.spans,x.flu); c=pearsonr(x.spans,x.share_w)
P(f"spans: r(spans,PPPL)={a[0]:+.3f}; r(spans,fluency)={b[0]:+.3f} (p={b[1]:.3f}); r(spans,share_w)={c[0]:+.3f}")
open('dialogue_share_summary.txt','w').write("F3 analysis (25 Oct 2026). Four-rater fluency means (R4 excluded). Dialogue share = words inside quoted spans / all words (segment.py v4).\n\n"+"\n".join(out)+"\n")
