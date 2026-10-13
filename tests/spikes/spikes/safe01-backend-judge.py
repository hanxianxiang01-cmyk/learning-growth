"""SAFE-01 trusted-answer path check with async DB/test doubles.
Imports the REAL service submit_attempt; no production DB or credential.
Proof scope: judge source, record_attempt receives raw response, no logs/network.
"""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'apps/learning-api'))
# Replace ONLY engine initialization: module imports would otherwise require
# psycopg even though this spike never connects to a database.
import types
from sqlalchemy.orm import DeclarativeBase
class TestBase(DeclarativeBase):
    pass
db_module = types.ModuleType('app.core.database')
db_module.Base = TestBase
sys.modules['app.core.database'] = db_module
from app.services import learning
from app.models import TaskInstance, ResourceVersion

class DB:
    async def get(self, model, identifier):
        if model == TaskInstance:
            return SimpleNamespace(child_id='qa-child', ability_id='app_rel', session_id='qa-session', resource_version_id='qa-resource')
        if model == ResourceVersion:
            return SimpleNamespace(content={'answer':63}, error_models=[], ui_schema={'schema_version':'2.0'})
        raise AssertionError(f'unexpected model {model}')
    async def commit(self):
        self.commits+=1
    commits=0

async def run_case(label, user_value, fake_client_expected, fake_client_status, expected_correct):
    observations=[]; db=DB()
    async def record_attempt_stub(_db, **kw):
        observations.append(kw)
        return {'correct':kw['correct'], 'next_action':{'type':'NEXT_TASK'}}
    response={'schema_version':'2.0','answer':{'value':user_value},'workspaces':[{'workspace_id':'main','data':{'evaluation':{'expected_answer':fake_client_expected,'status':fake_client_status},'state':{'answer':user_value}}}]}
    with patch.object(learning,'record_attempt',record_attempt_stub):
        result=await learning.submit_attempt(db,task_instance_id='qa-task',attempt_no=1,response=response)
    assert result['correct'] is expected_correct,(label,result)
    assert len(observations)==1
    assert observations[0]['response']==response
    assert db.commits==1
    return {'name':label,'server_correct':result['correct'],'client_claim':fake_client_status,'raw_response_forwarded_for_attempt_storage':True}

async def main():
    rows=[
        await run_case('forged_correct_but_wrong_answer',99,99,'CORRECT',False),
        await run_case('forged_incorrect_but_right_answer',63,99,'INCORRECT',True),
        await run_case('forged_expected_mismatch',99,63,'CORRECT',False),
    ]
    out={'schema':'safe01-backend-authority/1','scope':'real submit_attempt() with mocked db and record_attempt, not SQL write','cases':rows,'pass':len(rows),'real_db_tested':False,'raw_response_reaches_record_attempt':True,'final_grade_uses_db_resource_answer':True}
    if len(sys.argv)>1: Path(sys.argv[1]).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False,indent=2))

asyncio.run(main())
