import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import reference_updates as u

class UpdateTests(unittest.TestCase):
    def setup_job(self,folder,old=b'%PDF-old',new=b'%PDF-new'):
        root=Path(folder);stage=root/'update-staging'/'test';stage.mkdir(parents=True);(root/'beers-2023-paper.pdf').write_bytes(old);(stage/'beers-2023-paper.pdf').write_bytes(new)
        item={'id':'beers','title':'Beers','file':'beers-2023-paper.pdf','status':'changed','localHash':u.digest(old),'remoteHash':u.digest(new)}
        job={'id':'test','state':'checked','stage':str(stage),'items':[item]};u.JOBS['test']=job
        return root,job
    def test_check_never_updates_and_errors_not_same(self):
        with tempfile.TemporaryDirectory() as folder:
            root,job=self.setup_job(folder);job['items']=[]
            source={'id':'beers','title':'Beers','file':'beers-2023-paper.pdf','url':'https://example.test','kind':'pdf'}
            with patch.object(u,'DEST',root),patch.object(u,'SOURCES',[source]),patch.object(u,'download',return_value=b'%PDF-new'):u.run_check('test')
            self.assertEqual((root/source['file']).read_bytes(),b'%PDF-old');self.assertEqual(job['items'][0]['status'],'changed')
            job['items']=[]
            with patch.object(u,'DEST',root),patch.object(u,'SOURCES',[source]),patch.object(u,'download',side_effect=ValueError('network failed')):u.run_check('test')
            self.assertEqual(job['items'][0]['status'],'error')
    def test_update_archives_old_and_preserves_unselected(self):
        with tempfile.TemporaryDirectory() as folder:
            root,job=self.setup_job(folder);(root/'untouched.txt').write_text('keep')
            with patch.object(u,'DEST',root):u.run_update('test',['beers'])
            self.assertEqual(job['state'],'updated');self.assertEqual((root/'beers-2023-paper.pdf').read_bytes(),b'%PDF-new')
            backups=list((root/'已不參考').glob('*/beers-2023-paper.pdf'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_bytes(),b'%PDF-old')
            self.assertEqual((root/'untouched.txt').read_text(),'keep')
    def test_stale_check_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root,job=self.setup_job(folder);(root/'beers-2023-paper.pdf').write_bytes(b'%PDF-changed-after-check')
            with patch.object(u,'DEST',root):u.run_update('test',['beers'])
            self.assertEqual(job['state'],'update_failed');self.assertEqual((root/'beers-2023-paper.pdf').read_bytes(),b'%PDF-changed-after-check')
    def test_rollback_on_replace_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root,job=self.setup_job(folder);replace=u.os.replace
            def fail(src,dst):
                if Path(dst).name=='last-update.json':raise OSError('simulated disk failure')
                return replace(src,dst)
            with patch.object(u,'DEST',root),patch.object(u.os,'replace',side_effect=fail):u.run_update('test',['beers'])
            self.assertEqual(job['state'],'update_failed');self.assertEqual((root/'beers-2023-paper.pdf').read_bytes(),b'%PDF-old')
    def test_csv_diff(self):
        a='藥品代號,有效起日,有效迄日,成分\nAA,1,2,A\nBB,1,2,B\n'.encode('utf-8')
        b='藥品代號,有效起日,有效迄日,成分\nAA,1,2,C\nCC,1,2,D\n'.encode('utf-8')
        r=u.csv_changes(a,b,'nhi');self.assertEqual([r[k] for k in ['addedKeys','removedKeys','changedKeys']],[1,1,1])
    def test_same_not_allowed_update(self):
        with tempfile.TemporaryDirectory() as folder:
            root,job=self.setup_job(folder);job['items'][0]['status']='same'
            with self.assertRaises(ValueError):u.start_update('test',['beers'])

if __name__=='__main__':unittest.main()
