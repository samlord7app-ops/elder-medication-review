"""Presentation of existing rule findings, without adding clinical decisions."""
import re

def rows(results):
    output=[]
    for result in results:
        checks=result.get('clinicalChecks',[])
        # 過濾掉明確「條件未命中 (not_matched)」的無關規則（例如未併用該交互作用藥物、檢驗值未達危險門檻等）
        relevant=[c for c in checks if c['status']!='not_matched']
        if not relevant:
            status=result['status']
            risk_msg='本次處方未觸發高齡潛在不適當用藥、肝腎功能門檻或併用交互作用警示。' if status=='no_rule_hit' else result['reason']
            advice_msg='目前已檢核之條件未命中；仍請藥師結合病人完整病史與臨床狀況覆核。' if status=='no_rule_hit' else '請藥師確認藥品／保健食品成分、規格與適用準則，另行人工評估。'
            output.append(dict(drug=result['input'],ingredient=result.get('ingredient') or '',
                criterion='已檢核無觸發條款' if status=='no_rule_hit' else '無可對應的已執行條款',
                ruleId='',source='',status=status,
                risk=risk_msg,recommendation=advice_msg))
            continue
        for check in relevant:
            rule_id=check['id'];source=check['source']
            if source=='beers':
                match=re.match(r'BEERS-T(\d+)',rule_id)
                criterion='Beers 2023'+(' 表 '+match[1] if match else '')+'（系統分支 '+rule_id+'）'
            elif source=='stopp-start':
                match=re.match(r'STOPP-([A-M]\d+)',rule_id)
                criterion='STOPP v3 '+(match[1] if match else rule_id)+'（系統分支 '+rule_id+'）'
            elif source=='pim-taiwan':
                match=re.match(r'PIM-TW-T(\d+)',rule_id)
                criterion='PIM-Taiwan 2018'+(' 表 '+match[1] if match else '')+'（系統分支 '+rule_id+'）'
            elif source=='organ-safety':
                criterion='肝腎功能劑量與禁忌篩檢（'+rule_id+'）'
            elif source=='supplement-safety':
                criterion='保健食品／中西藥交互作用（'+rule_id+'）'
            else:
                criterion=source+'（'+rule_id+'）'
            status=check['status']
            advice={
                'potential_risk':'請醫師／藥師覆核必要性、適應症及個別風險，評估是否調整、錯開服用或採替代治療；勿自行停藥。',
                'insufficient_data':'先補齊並確認：'+'、'.join(check.get('missing',[]))+'；資料不足，尚不能判定本條款。',
                'source_unverified':'先於本機取得並驗證相符的原始文獻版本，再重新評估；本條款尚未形成有效臨床結論。',
                'exception_requires_review':'請醫師／藥師確認例外適應症、效益與風險，並記錄覆核理由；不等同安全。',
                'not_matched':'本次已執行條件未命中；仍需人工檢視其他準則與完整病史，不能視為安全。'
            }[status]
            if check.get('note'):advice+=' 規則補充：'+check['note']
            output.append(dict(drug=result['input'],ingredient=result.get('ingredient') or '',
                criterion=criterion,ruleId=rule_id,source=source,status=status,
                risk=check['title'],recommendation=advice))
    return output
