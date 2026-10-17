import sys
from pathlib import Path

from jinja2 import TemplateError
from jinja2.sandbox import ImmutableSandboxedEnvironment


def validate_template(template_path):
    environment = ImmutableSandboxedEnvironment(
        trim_blocks=True, lstrip_blocks=True, extensions=['jinja2.ext.loopcontrols'])

    def raise_template_error(message):
        raise TemplateError(message)

    environment.globals['raise_exception'] = raise_template_error
    template = environment.from_string(Path(template_path).read_text())
    messages = [{'role': 'user', 'content': 'LOCAL_TEXT_CHECK'}]
    render_options = {'enable_thinking': False, 'add_generation_prompt': True}
    if 'LOCAL_TEXT_CHECK' not in template.render(messages=messages, **render_options):
        raise RuntimeError('Qwen template did not preserve ordinary text.')
    tool_result = {'role': 'tool', 'content': [
        {'type': 'text', 'text': 'LOCAL_TOOL_RESULT_CHECK'},
        {'type': 'tool_reference', 'tool_name': 'LocalRead'},
        {'type': 'tool_reference', 'name': 'LocalInspect'},
        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,fixture'}}]}
    t = template.render(messages=messages + [tool_result], **render_options)
    for s in ('LOCAL_TOOL_RESULT_CHECK', '<tool_reference>LocalRead</tool_reference>',
              '<tool_reference>LocalInspect</tool_reference>', '<|image_pad|>'):
        if s not in t:
            raise RuntimeError('Qwen template content compatibility check failed: ' + s)
    try:
        template.render(messages=[{'role': 'user', 'content': [{'type': 'unknown_local_probe'}]}],
                     **render_options)
    except TemplateError:
        return
    raise RuntimeError('Qwen template silently accepted an unknown content type.')


if __name__ == '__main__':
    validate_template(sys.argv[1])
    print('Qwen template text/tool_reference/image checks passed.')
