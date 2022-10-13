from dataclasses import dataclass, field
from dataclass_wizard import YAMLWizard
from jinja2 import Template
from typing import Any, Dict, List, Optional
from b_theme import load_theme

import os
import sys
import re
import shlex
import shutil
import subprocess


TEMPLATES_CONFIG_DEFAULT_PATH = os.path.expanduser(
    '~/.config/theme/templates.yml')


@dataclass
class ThemeTemplate(YAMLWizard):
    variables: Dict[str, Any] = field(default_factory=dict)
    template: Optional[str] = field(default_factory=lambda: None)
    destination: Optional[str] = field(default_factory=lambda: None)
    unaltered: List[str] = field(default_factory=list)
    pre_hook: List[str] = field(default_factory=list)
    post_hook: List[str] = field(default_factory=list)


@dataclass
class ThemeTemplateConfig(YAMLWizard):
    variables: Dict[str, Any] = field(default_factory=dict)
    pipelines: Dict[str, List[str]] = field(default_factory=dict)
    templates: Dict[str, ThemeTemplate] = field(default_factory=dict)


def load_template_configs(path: str = TEMPLATES_CONFIG_DEFAULT_PATH) -> List[ThemeTemplateConfig]:
    try:
        config = ThemeTemplateConfig.from_yaml_file(path)
        return [config] if isinstance(config, ThemeTemplateConfig) else config
    except Exception as e:
        print('Config error: ', e)
        return []


def _render_from_dir(template_path: str, destination_path: str, unaltered: List[str], substitutions: Dict[str, Any]) -> None:
    for entry in os.listdir(template_path):
        _render(
            os.path.join(template_path, entry),
            os.path.join(destination_path, entry),
            unaltered,
            substitutions
        )


def _render_file(template_path: str, destination_path: str, unaltered: List[str], substitutions: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)

    if any(re.match(p, template_path) for p in unaltered):
        shutil.copyfile(template_path, destination_path, follow_symlinks=True)
    else:
        print('>> ', template_path)
        with open(template_path, mode='r') as t:
            doc = Template(t.read()).render(**substitutions)
        print('<< ', destination_path)
        with open(destination_path, "w") as d:
            d.write(doc)


def _render(template_path: str, destination_path: str, unaltered: List[str], substitutions: Dict[str, Any]) -> None:
    if os.path.isdir(template_path):
        _render_from_dir(template_path, destination_path,
                         unaltered, substitutions)
    else:
        _render_file(template_path, destination_path,
                     unaltered, substitutions)


def _run_hook(hook: List[str], substitutions: Dict[str, Any]) -> None:
    for line in hook:
        cmd = shlex.split(Template(line).render(**substitutions))
        subprocess.run(cmd).check_returncode()


def _generate(template_path: str, destination_path: str, unaltered: List[str], substitutions: Dict[str, Any]) -> None:
    if template_path and destination_path:
        template_path = os.path.expanduser(
            Template(template_path).render(**substitutions))
        destination_path = os.path.expanduser(
            Template(destination_path).render(**substitutions))
        if os.path.exists(template_path):
            _render(template_path, destination_path,
                    unaltered, substitutions)


def _update_template(template: ThemeTemplate, substitutions: Dict[str, Any]) -> None:
    substitutions = {**substitutions, **template.variables}
    try:
        _run_hook(template.pre_hook, substitutions)
        _generate(template.template, template.destination,
                  template.unaltered, substitutions)
        _run_hook(template.post_hook, substitutions)
    except Exception as e:
        print('Execution Error: ', e)


def _update_all(templates: List[ThemeTemplate], substitutions: Dict[str, Any]) -> None:
    for template in templates:
        _update_template(template, substitutions)


def _update_some(template_names: List[str], templates: Dict[str, ThemeTemplate], substitutions: Dict[str, Any]) -> None:
    for name in template_names:
        if name in templates:
            _update_template(templates[name], substitutions)
        else:
            print(f'Config Error: Skipping {name}. Reason: Not defined')


def _update_pipelines(pipeline_names: List[str], pipelines: Dict[str, list[str]], templates: Dict[str, ThemeTemplate],  substitutions: Dict[str, Any]) -> None:
    for pipeline_name in pipeline_names:
        print('\n', pipeline_name, '\n', '-', '-'*len(pipeline_name), '_')
        try:
            pipeline = pipelines[pipeline_name]
            for template_name in pipeline:
                _update_template(templates[template_name], substitutions)
        except Exception as e:
            print('Config Error: ', e)


def main():
    theme = load_theme()
    env = {k: v for k, v in os.environ.items()}
    substitutions = {'theme': theme, 'env': env}

    argv = sys.argv
    argn = len(argv) - 1

    if argn == 0:
        for config in load_template_configs():
            _substitutions = {**substitutions, **config.variables}
            _update_all(config.templates.values(), _substitutions)
    elif argv[1] == 'on':
        pipeline_names = argv[2:]
        for config in load_template_configs():
            _substitutions = {**substitutions, **config.variables}
            _update_pipelines(pipeline_names, config.pipelines,
                              config.templates, _substitutions)
    else:
        template_names = argv[1:]
        for config in load_template_configs():
            _substitutions = {**substitutions, **config.variables}
            _update_some(template_names,
                         config.templates, _substitutions)
