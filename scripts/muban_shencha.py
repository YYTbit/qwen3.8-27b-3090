import sys
from pathlib import Path

from jinja2 import TemplateError
from jinja2.sandbox import ImmutableSandboxedEnvironment


def shencha(lujing):
    huanjing = ImmutableSandboxedEnvironment(
        trim_blocks=True, lstrip_blocks=True, extensions=['jinja2.ext.loopcontrols'])

    def baocuo(neirong):
        raise TemplateError(neirong)

    huanjing.globals['raise_exception'] = baocuo
    muban = huanjing.from_string(Path(lujing).read_text())
    ji = [{'role': 'user', 'content': 'LOCAL_TEXT_CHECK'}]
    canshu = {'enable_thinking': False, 'add_generation_prompt': True}
    if 'LOCAL_TEXT_CHECK' not in muban.render(messages=ji, **canshu):
        raise RuntimeError('Qwen template did not preserve ordinary text.')
    fanhui = {'role': 'tool', 'content': [
        {'type': 'text', 'text': 'LOCAL_TOOL_RESULT_CHECK'},
        {'type': 'tool_reference', 'tool_name': 'LocalRead'},
        {'type': 'tool_reference', 'name': 'LocalInspect'},
        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,fixture'}}]}
    t = muban.render(messages=ji + [fanhui], **canshu)
    for s in ('LOCAL_TOOL_RESULT_CHECK', '<tool_reference>LocalRead</tool_reference>',
              '<tool_reference>LocalInspect</tool_reference>', '<|image_pad|>'):
        if s not in t:
            raise RuntimeError('Qwen template content compatibility check failed: ' + s)
    try:
        muban.render(messages=[{'role': 'user', 'content': [{'type': 'unknown_local_probe'}]}],
                     **canshu)
    except TemplateError:
        return
    raise RuntimeError('Qwen template silently accepted an unknown content type.')


if __name__ == '__main__':
    shencha(sys.argv[1])
    print('Qwen template text/tool_reference/image checks passed.')
