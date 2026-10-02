import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HUMAN = ROOT / 'skills/li-human/scripts'
CONTEXT = ROOT / 'skills/li-context/scripts/context.py'
sys.path.insert(0, str(HUMAN))
from humanize import humanize, load_lexicon
from detect import analyze


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


ctx = module('context', CONTEXT)
installer = module('installer', ROOT / 'scripts/install_skills.py')


def cli(script, *args, input=None, cwd=None):
    return subprocess.run([sys.executable, str(script), *map(str, args)], input=input,
                          text=True, capture_output=True, cwd=cwd, timeout=15)


def record(**changes):
    return {'id': 'p1', 'date': '2026-10-02', 'topic': 'proposal review',
            'angle': 'missing dependency', 'hook': 'The checklist missed a dependency.',
            'body': 'We found a dependency missing from the review.', 'cta': '',
            'tags': [], 'source_material': [], 'anecdotes': ['lost review checklist'],
            'claims': ['a dependency was missing'], 'metrics': {}, **changes}


class HumanizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = load_lexicon()

    def clean(self, text, **kwargs):
        return humanize(text, self.lex, **kwargs)[0]

    def test_zero_width_space(self):
        self.assertEqual(self.clean('a\u200bb\ufeffc'), 'abc\n')

    def test_nonbreaking_spaces(self):
        self.assertEqual(self.clean('a\u00a0b\u202fc'), 'a b c\n')

    def test_curly_quotes(self):
        self.assertEqual(self.clean('“Hi,” she said. It’s fine.'), '"Hi," she said. It\'s fine.\n')

    def test_dashes(self):
        self.assertEqual(self.clean('One—two. 5–10. x – y'), 'One, two. 5-10. x, y\n')

    def test_ellipsis(self):
        self.assertEqual(self.clean('Wait…'), 'Wait...\n')

    def test_urls(self):
        text = 'https://example.com/leverage?x=“robust” www.example.com/delve'
        self.assertEqual(self.clean(text), text+'\n')

    def test_email(self):
        self.assertEqual(self.clean('leverage@example.com'), 'leverage@example.com\n')

    def test_capitalization(self):
        self.assertEqual(self.clean('LEVERAGE Leverage leverage'), 'USE Use use\n')

    def test_phrase_longest_first(self):
        self.assertEqual(self.clean('Delve into this.'), 'Look at this.\n')

    def test_phrase_ending_punctuation(self):
        self.assertEqual(self.clean('What are your thoughts?'), '')

    def test_phrase_not_across_paragraphs(self):
        self.assertEqual(self.clean('in order\n\nto go'), 'in order\n\nto go\n')

    def test_structural_flag(self):
        _, report = humanize("It's not just speed, it's accuracy.", self.lex)
        self.assertTrue(any('not just' in f['name'] for f in report['structures']))

    def test_empty(self):
        self.assertEqual(self.clean(''), '')

    def test_unicode(self):
        self.assertEqual(self.clean('مرحبا 中文 café 👩\u200d💻 فارسی\u200cها'), 'مرحبا 中文 café 👩\u200d💻 فارسی\u200cها\n')

    def test_subdivision_flag_preserved(self):
        flag='\U0001f3f4\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f'
        self.assertEqual(self.clean(flag),flag+'\n')

    def test_stray_tag_removed(self):
        self.assertEqual(self.clean('Hello\U000e0067'),'Hello\n')

    def test_aggressive_opt_in(self):
        self.assertEqual(self.clean('a\u200db', aggressive=True), 'ab\n')

    def test_clean_input(self):
        self.assertEqual(self.clean('I fixed the test.\n'), 'I fixed the test.\n')

    def test_no_lexical(self):
        self.assertEqual(self.clean('leverage', lexical=False), 'leverage\n')

    def test_no_typography(self):
        self.assertEqual(self.clean('“Hi”', typography=False), '“Hi”\n')

    def test_placeholder_collision(self):
        self.assertIn('\x00URL0\x00', self.clean('\x00URL0\x00 https://example.com'))

    def test_json_report(self):
        p = cli(HUMAN/'humanize.py', '--json', input='Leverage')
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['text'], 'Use\n')
        self.assertEqual(result['report']['lexical'][0]['count'], 1)

    def test_report_to_stderr(self):
        p = cli(HUMAN/'humanize.py', '--report', input='Leverage')
        self.assertEqual(p.stdout, 'Use\n')
        self.assertIn('style changes', p.stderr)

    def test_output_exclusive(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d)/'a'; source.write_text('Leverage')
            p = cli(HUMAN/'humanize.py', source, '-o', source)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(source.read_text(), 'Leverage')
            output=Path(d)/'out'
            self.assertEqual(cli(HUMAN/'humanize.py', source, '-o', output).returncode, 0)
            self.assertEqual(output.read_text(), 'Use\n')

    def test_output_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'target';target.write_text('keep')
            link=Path(d)/'link';link.symlink_to(target)
            self.assertEqual(cli(HUMAN/'humanize.py', '-o', link, input='new').returncode, 2)
            self.assertEqual(target.read_text(), 'keep')

    def test_malformed_lexicon_types(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'lex.json'
            for data in ([], {'invisible':[]}, {**load_lexicon(),'words':['bad']},
                         {**load_lexicon(),'invisible':[{'cp':'U+FFFFFFFF','name':'bad','action':'delete'}]}):
                path.write_text(json.dumps(data))
                p=cli(HUMAN/'humanize.py','--lexicon',path,input='hello')
                self.assertEqual(p.returncode,2,p.stderr)
                self.assertNotIn('Traceback',p.stderr)

    def test_bad_regex(self):
        with tempfile.TemporaryDirectory() as d:
            lex=load_lexicon();lex['structures'][0]['regex']='['
            path=Path(d)/'lex.json';path.write_text(json.dumps(lex))
            p=cli(HUMAN/'humanize.py','--lexicon',path,input='hello')
            self.assertEqual(p.returncode,2)
            self.assertNotIn('Traceback',p.stderr)

    def test_dash_preserves_paragraph(self):
        self.assertIn('\n\n',self.clean('First.\n\n— Next.'))

    def test_bad_lexicon(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'lex.json';path.write_text('{}')
            p=cli(HUMAN/'humanize.py', '--lexicon', path, input='hello')
            self.assertEqual(p.returncode, 2)
            self.assertNotIn('Traceback', p.stderr)

    def test_missing_input(self):
        p=cli(HUMAN/'humanize.py', '/nonexistent/draft.txt')
        self.assertEqual(p.returncode, 2)
        self.assertNotIn('Traceback', p.stderr)


class QualityTests(unittest.TestCase):
    def panel(self, text):
        return analyze(text, load_lexicon())

    def test_empty(self):
        p=self.panel('')
        self.assertEqual(p['word_count'], 0)
        self.assertIsNone(p['sentence_variation']['coefficient'])

    def test_short(self):
        self.assertIsNone(self.panel('One small thought.')['sentence_variation']['coefficient'])

    def test_long(self):
        p=self.panel('We checked the build and found the issue. '*1000)
        self.assertEqual(p['sentence_count'], 1000)
        self.assertEqual(p['sentence_variation']['coefficient'], 0)

    def test_repetitive(self):
        self.assertEqual(len(self.panel('Same sentence. Same sentence.')['structural_repetition']['repeated_sentences']),1)

    def test_mixed_length(self):
        p=self.panel('Done. I checked the build. It passed after we fixed one dependency. The change made reviews much easier because the checklist now captures the missing step.')
        self.assertGreater(p['sentence_variation']['coefficient'], .5)

    def test_unicode_word_count(self):
        self.assertEqual(self.panel('café 中文 مرحبا')['word_count'],3)

    def test_urls_excluded_from_generic_count(self):
        self.assertEqual(self.panel('https://example.com/leverage')['generic_language']['hits'],[])

    def test_no_authorship_score(self):
        p=cli(HUMAN/'detect.py', '--json', input='Hello.')
        self.assertEqual(p.returncode,0)
        self.assertNotIn('human_score',json.loads(p.stdout))
        self.assertIn('not proof of authorship',p.stdout)

    def test_compare(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a';a.write_text('Leverage this.')
            b=Path(d)/'b';b.write_text('Use this.')
            p=cli(HUMAN/'detect.py', a,b,'--json')
            panels=json.loads(p.stdout)
            self.assertEqual(len(panels),2)
            self.assertGreater(panels[0]['generic_language']['per_100_words'],panels[1]['generic_language']['per_100_words'])


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'.linkedin-agent'

    def test_missing(self):
        self.assertEqual(ctx.profile_status(self.root)['status'],'missing')

    def test_init_partial(self):
        created=ctx.initialize(self.root)
        self.assertEqual(len(created),14)
        self.assertEqual(ctx.profile_status(self.root)['status'],'partial')

    def test_init_preserves(self):
        ctx.initialize(self.root)
        p=self.root/'identity/voice.md';p.write_text('My actual voice')
        self.assertEqual(ctx.initialize(self.root),[])
        self.assertEqual(p.read_text(),'My actual voice')

    def test_complete(self):
        ctx.initialize(self.root)
        for p in self.root.rglob('*.md'):
            p.write_text('Explicitly reviewed public context; no unknown fields.')
        self.assertEqual(ctx.profile_status(self.root)['status'],'complete')

    def test_partial_missing(self):
        (self.root/'identity').mkdir(parents=True)
        (self.root/'identity/voice.md').write_text('My voice')
        self.assertEqual(ctx.profile_status(self.root)['status'],'partial')

    def test_empty_history(self):
        self.assertEqual(ctx.load_history(self.root),[])
        self.assertEqual(ctx.summarize(self.root)['posts'],0)

    def test_append_load(self):
        ctx.append_history(self.root,record(),True)
        self.assertEqual(ctx.load_history(self.root),[record()])

    def test_requires_publication(self):
        with self.assertRaises(ValueError):ctx.append_history(self.root,record())
        self.assertFalse(self.root.exists())

    def test_strict_date_shape(self):
        for invalid in ('20261002','2026-W40-5'):
            with self.subTest(date=invalid),self.assertRaises(ValueError):
                ctx.append_history(self.root,record(date=invalid),True)

    def test_requires_date(self):
        r=record();r.pop('date')
        with self.assertRaises(ValueError):ctx.append_history(self.root,r,True)

    def test_duplicate_id(self):
        ctx.append_history(self.root,record(),True)
        with self.assertRaises(ValueError):ctx.append_history(self.root,record(),True)
        self.assertEqual(len(ctx.load_history(self.root)),1)

    def test_last_line_without_newline(self):
        ctx.initialize(self.root)
        (self.root/'history/posts.jsonl').write_text(json.dumps(record()))
        ctx.append_history(self.root,record(id='p2'),True)
        self.assertEqual(len(ctx.load_history(self.root)),2)

    def test_malformed_line(self):
        ctx.initialize(self.root)
        p=self.root/'history/posts.jsonl';p.write_text(json.dumps(record())+'\nnot json\n')
        with self.assertRaisesRegex(ValueError,'line 2'):ctx.load_history(self.root)
        before=p.read_text()
        with self.assertRaises(ValueError):ctx.append_history(self.root,record(id='p2'),True)
        self.assertEqual(p.read_text(),before)

    def test_bad_schema(self):
        for changes in ({'date':'yesterday'},{'topic':4},{'metrics':{'impressions':float('nan')}},{'metrics':{'x':-1}},{'tags':[4]}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):ctx.append_history(self.root,record(**changes),True)

    def test_hook_topic_anecdote_claim_duplicates(self):
        result=ctx.duplicates(record(),[record()])
        fields={x['field'] for x in result[0]['reasons']}
        self.assertTrue({'hook','topic','anecdotes','claims','body'}.issubset(fields))

    def test_same_topic_new_angle_not_rejected(self):
        result=ctx.duplicates(record(angle='pricing clarity',hook='Price changes the conversation.',body='New proof about pricing.'),[record()])
        self.assertTrue(result)
        self.assertIn('does not reject',result[0]['decision'])

    def test_unrelated_no_duplicate(self):
        self.assertEqual(ctx.duplicates({'topic':'hiring developers','hook':'Small teams need mentors'},[record()]),[])

    def test_summary_performance_neglected(self):
        ctx.initialize(self.root)
        ctx.append_history(self.root,record(),True)
        (self.root/'history/topics.json').write_text(json.dumps({'themes':['proposal review','hiring']}))
        (self.root/'analytics/performance.csv').write_text('id,impressions,reactions,comments,reposts\np1,100,5,3,2\n')
        result=ctx.summarize(self.root)
        self.assertEqual(result['successful_examples'][0]['engagement_rate'],.1)
        self.assertEqual(result['neglected_themes'],['hiring'])

    def test_missing_metrics_not_zero(self):
        ctx.append_history(self.root,record(metrics={'impressions':100,'reactions':5}),True)
        self.assertEqual(ctx.summarize(self.root)['successful_examples'],[])

    def test_bad_topics(self):
        ctx.initialize(self.root)
        (self.root/'history/topics.json').write_text('{')
        with self.assertRaises(ValueError):ctx.profile_status(self.root)

    def test_bad_csv(self):
        ctx.initialize(self.root)
        (self.root/'analytics/performance.csv').write_text('id,impressions,reactions,comments,reposts\np1,NaN,1,2,3\n')
        with self.assertRaises(ValueError):ctx.summarize(self.root)

    def test_invalid_kind_no_write(self):
        with self.assertRaises(ValueError):ctx.append_history(self.root,record(),True,'unknown')
        self.assertFalse(self.root.exists())

    def test_csv_column_counts(self):
        ctx.initialize(self.root)
        path=self.root/'analytics/performance.csv'
        for row in ('p1,100,5,3,2,extra','p1,100,5,3'):
            path.write_text('id,impressions,reactions,comments,reposts\n'+row+'\n')
            with self.subTest(row=row),self.assertRaises(ValueError):ctx.summarize(self.root)

    def test_csv_duplicate_headers(self):
        ctx.initialize(self.root)
        (self.root/'analytics/performance.csv').write_text('id,impressions,reactions,comments,reposts,reactions\np1,100,5,3,2,50\n')
        with self.assertRaises(ValueError):ctx.summarize(self.root)

    def test_comment_history(self):
        ctx.append_history(self.root,record(),True,'comments')
        self.assertEqual(len(ctx.load_history(self.root,'comments')),1)
        self.assertEqual(ctx.load_history(self.root),[])

    def test_path_traversal(self):
        with self.assertRaises(ValueError):ctx.safe_path(self.root,'../outside')

    def test_symlink_directory(self):
        self.root.symlink_to(Path(self.temp.name))
        with self.assertRaises(ValueError):ctx.initialize(self.root)

    def test_symlink_file(self):
        ctx.initialize(self.root)
        p=self.root/'history/posts.jsonl';p.unlink();p.symlink_to(Path(self.temp.name)/'outside')
        with self.assertRaises(ValueError):ctx.append_history(self.root,record(),True)
        self.assertFalse((Path(self.temp.name)/'outside').exists())

    def test_cli(self):
        p=cli(CONTEXT,'--root',self.root,'init')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertTrue(json.loads(p.stdout)['created'])
        candidate=Path(self.temp.name)/'candidate.json';candidate.write_text('[]')
        p=cli(CONTEXT,'--root',self.root,'check',candidate)
        self.assertEqual(p.returncode,2)
        self.assertNotIn('Traceback',p.stderr)


class ResourceTests(unittest.TestCase):
    def test_skill_inventory_and_frontmatter(self):
        skills=list((ROOT/'skills').glob('*/SKILL.md'))
        self.assertEqual(len(skills),20)
        for p in skills:
            s=p.read_text()
            self.assertTrue(s.startswith('---\nname: '+p.parent.name+'\n'))
            description=s.split('description: ',1)[1].splitlines()[0]
            self.assertTrue(json.loads(description))
            self.assertLess(len(s.split()),450)
            metadata=p.parent/'agents/openai.yaml'
            self.assertIn('allow_implicit_invocation: true',metadata.read_text())
            self.assertIn('$'+p.parent.name,metadata.read_text())

    def test_all_skill_reference_links(self):
        for p in (ROOT/'skills').rglob('*.md'):
            for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if '://' not in link:
                    self.assertTrue((p.parent/link).is_file(),f'{p}: {link}')

    def test_json_resources(self):
        # Validate every bundled resource/manifest, not ignored user data or
        # third-party dependency fixtures (which may intentionally use JSONC).
        resources = [*ROOT.glob('*.json'), *(ROOT/'skills').rglob('*.json'),
                     *(ROOT/'templates').rglob('*.json'), *(ROOT/'tools/web').glob('*.json')]
        for p in resources:
            json.loads(p.read_text())
        hooks=json.loads((ROOT/'skills/li-post/references/hooks.json').read_text())
        self.assertEqual(len(hooks['hooks']),21)
        self.assertEqual(len({x['id'] for x in hooks['hooks']}),21)
        rubric=json.loads((ROOT/'skills/li-profile/references/rubric.json').read_text())
        self.assertEqual(sum(x['points'] for x in rubric['items']),100)
        self.assertEqual(len(rubric['items']),12)
        for pattern in load_lexicon()['structures']:re.compile(pattern['regex'])

    def test_no_legacy_runtime_paths(self):
        for p in (ROOT/'skills').rglob('*'):
            if p.is_file() and p.suffix in ('.md','.py','.json','.yaml'):
                self.assertNotIn('~/.claude',p.read_text())

    def test_license_unchanged(self):
        p=subprocess.run(['git','show','HEAD:LICENSE'],cwd=ROOT,capture_output=True,check=True)
        self.assertEqual(p.stdout,(ROOT/'LICENSE').read_bytes())

    def test_installed_pack_paths_and_cli(self):
        with tempfile.TemporaryDirectory(prefix='linkedin skills ') as d:
            dest=Path(d)/'project/.agents/skills'
            self.assertEqual(len(installer.install(dest)),20)
            for p in dest.glob('*/SKILL.md'):
                for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                    if '://' not in link:self.assertTrue((p.parent/link).is_file())
            self.assertEqual(cli(dest/'li-human/scripts/humanize.py','--json',input='Leverage',cwd=d).returncode,0)
            self.assertEqual(cli(dest/'li-human/scripts/detect.py','--json',input='hello',cwd=d).returncode,0)
            self.assertEqual(cli(dest/'li-context/scripts/context.py','--root',Path(d)/'profile','init',cwd=d).returncode,0)
            self.assertTrue((dest/'linkedin-agent-LICENSE').is_file())
            self.assertEqual(cli(dest/'li-read/scripts/read_layer.py','--root',Path(d)/'profile','status',cwd=d).returncode,0)
            self.assertEqual(cli(dest/'li-read/scripts/intelligence.py','--root',Path(d)/'profile','brief',cwd=d).returncode,0)
            self.assertEqual(cli(dest/'li-read/scripts/intelligence.py','--root',Path(d)/'profile','weekly',cwd=d).returncode,0)
            with self.assertRaises(ValueError):installer.install(dest)

    def test_install_conflict_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d);(dest/'li-post').mkdir()
            with self.assertRaises(ValueError):installer.install(dest)
            self.assertFalse((dest/'li-human').exists())

    def test_install_attribution_symlink_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)
            (dest/'linkedin-agent-LICENSE').symlink_to(dest/'outside')
            with self.assertRaises(ValueError):installer.install(dest)
            self.assertFalse((dest/'li-post').exists())

    def test_install_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            link=Path(d)/'link';link.symlink_to(Path(d))
            with self.assertRaises(ValueError):installer.install(link)


if __name__ == '__main__':
    unittest.main()
