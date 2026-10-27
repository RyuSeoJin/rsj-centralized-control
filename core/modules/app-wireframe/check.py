"""와이어프레임 입력·대상·기준 키트의 검사를 실행합니다."""
# CHANGELOG · 2026-10-14: Design/FigJam 구분과 미연결 키트 제작 차단 검사.
import copy
import sys
import tempfile
from pathlib import Path
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root/'scripts'))
import wireframe as w
for path in ('module.md','module.json','rules/wireframe.md','scripts/wireframe.py'):
    assert (root/path).is_file(), path
with tempfile.TemporaryDirectory() as tmp:
    base=Path(tmp)
    (base/'spec.md').write_text('example',encoding='utf-8')
    data={'schemaVersion':1,'revision':'example-1','target':{'designUrl':'https://www.figma.com/design/example/name'},
          'sources':[{'path':'spec.md','revision':'example-1'}], 'kits':[{'id':'kit-example'}], 'selectedKit':'kit-example',
          'kitBinding':{'libraryKey':'example','accessEvidence':'verified in test','usageEvidence':'verified in test','styleEvidence':'verified in test'},
          'components':{'button':{'kitId':'kit-example','nodeId':'1:2','verifiedTargetFileKey':'example'}},
          'screens':[{'id':'screen-example','mode':'common','roles':['button'],'sourceRefs':['spec-example'],
                      'entrySteps':['open'],'elements':[{'role':'button'}],'observationEvidence':'test fixture'}]}
    assert not w.inspect(data,base)['ready']  # source inspection alone is insufficient
    data['screens'][0]['renderEvidence']={'method':'user-screenshot','reference':'fixture.png',
        'state':'example state','capturedAt':'2026-01-01','viewport':{'width':390,'height':844}}
    assert w.inspect(data,base)['ready']
    for field in ('reference','state','capturedAt','viewport'):
        broken=copy.deepcopy(data);broken['screens'][0]['renderEvidence'].pop(field)
        assert not w.inspect(broken,base)['ready']
    broken=copy.deepcopy(data);broken['screens'][0]['renderEvidence']['method']='source-only'
    assert not w.inspect(broken,base)['ready']

    assert w.plan(data,w.inspect(data,base))==w.plan(data,w.inspect(data,base))
    broken=copy.deepcopy(data);broken['target']['designUrl']='https://www.figma.com/board/example/name'
    assert not w.inspect(broken,base)['valid']
    broken=copy.deepcopy(data);broken['selectedKit']=None;broken['kitBinding']={}
    assert w.inspect(broken,base)['valid'] and not w.inspect(broken,base)['ready']
    broken=copy.deepcopy(data);broken['components']['button']['verifiedTargetFileKey']='other-file'
    assert not w.inspect(broken,base)['ready']
    broken=copy.deepcopy(data);broken['screens']*=2
    assert not w.inspect(broken,base)['valid']
    broken=copy.deepcopy(data);broken['components']['button']['kitId']='other-kit'
    assert not w.inspect(broken,base)['valid']
    broken=copy.deepcopy(data);broken['transitions']=[{'from':'screen-example','to':'missing','action':'tap'}]
    assert not w.inspect(broken,base)['valid']
print('app-wireframe: input, readiness, target, mapping and deterministic plan checks passed')
