from dataclasses import dataclass, field
from dataclass_wizard import YAMLWizard
from jinja2 import Template
from typing import Any, Dict, Generator, List, Optional
from b_theme import load_theme
from tqdm import tqdm

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


@dataclass
class TemplateFileDetails(YAMLWizard):
    template_path: str
    destination_path: str
    substitutions:  Dict[str, Any] = field(default_factory=dict)


def load_template_configs(path: str = TEMPLATES_CONFIG_DEFAULT_PATH) -> List[ThemeTemplateConfig]:
    try:
        config = ThemeTemplateConfig.from_yaml_file(path)
        return [config] if isinstance(config, ThemeTemplateConfig) else config
    except Exception as e:
        print('Config error: ', e)
        return []


def _find_templates(template_path: str, destination_path: str, unaltered: List[str], substitutions: Dict[str, Any]) -> Generator[TemplateFileDetails, None, None]:
    if os.path.isdir(template_path):
        for entry in os.listdir(template_path):
            for template in _find_templates(
                os.path.join(template_path, entry),
                os.path.join(destination_path, entry),
                unaltered, substitutions
            ):
                yield template
    else:
        print (template_path, end="\r")
        if any(re.match(p, template_path) for p in unaltered):
            yield TemplateFileDetails(template_path, destination_path)
        else:
            yield TemplateFileDetails(template_path, destination_path, substitutions)


def _render_templates(templates_details: List[TemplateFileDetails]) -> None:
    for templates_detail in tqdm(templates_details, unit=''):
        os.makedirs(os.path.dirname(
            templates_detail.destination_path), exist_ok=True)
        if templates_detail.substitutions:
            with open(templates_detail.template_path, mode='r') as temp:
                doc = Template(temp.read()).render(
                    **templates_detail.substitutions)
            with open(templates_detail.destination_path, "w") as dest:
                dest.write(doc)
        else:
            shutil.copyfile(templates_detail.template_path, templates_detail. destination_path,
                            follow_symlinks=True)


def _run_hook(hook: List[str], substitutions: Dict[str, Any]) -> None:
    for line in hook:
        cmd = shlex.split(Template(line).render(**substitutions))
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ).check_returncode()


def _generate(template_path: str, destination_path: str, unaltered: List[str], substitutions: Dict[str, Any]) -> None:
    if template_path and destination_path:
        template_path = os.path.expanduser(
            Template(template_path).render(**substitutions))
        destination_path = os.path.expanduser(
            Template(destination_path).render(**substitutions))
        if os.path.exists(template_path):
            _render_templates(list(_find_templates(
                template_path, destination_path, unaltered, substitutions)))


def _update_template(template: ThemeTemplate, substitutions: Dict[str, Any]) -> None:
    substitutions = {**substitutions, **template.variables}
    try:
        _run_hook(template.pre_hook, substitutions)
        _generate(template.template, template.destination,
                  template.unaltered, substitutions)
        _run_hook(template.post_hook, substitutions)
    except Exception as e:
        print('Execution Error: ', e)


def _update_templates(templates: Dict[str, ThemeTemplate], substitutions: Dict[str, Any]) -> None:
    for template_name, template in templates.items():
        print(template_name)
        _update_template(template, substitutions)


def update_all_templates(substitutions: Dict[str, any]) -> None:
    for config in load_template_configs():
        _substitutions = {**substitutions, **config.variables}
        _update_templates(config.templates, _substitutions)


def update_select_templates(template_names: List[str], substitutions: Dict[str, any]) -> None:
    for config in load_template_configs():
        _substitutions = {**substitutions, **config.variables}
        templates = {
            t_name: config.templates[t_name]
            for t_name in set(template_names).intersection(config.templates)
        }
        _update_templates(templates, _substitutions)


def update_pipeline_templates(pipeline_names: List[str], substitutions: Dict[str, any]) -> None:
    for config in load_template_configs():
        _substitutions = {**substitutions, **config.variables}
        for p_name in set(pipeline_names).intersection(config.pipelines):
            print('\n\t', p_name, '\n\t', '='*len(p_name))
            templates = {
                t_name: config.templates[t_name]
                for t_name in set(config.pipelines[p_name]).intersection(config.templates)
            }
            _update_templates(templates, _substitutions)


def main():
    theme = load_theme()

    env = {k: v for k, v in os.environ.items()}
    substitutions = {'theme': theme, 'env': env}

    argv = sys.argv
    argn = len(argv) - 1

    if argn == 0:
        update_all_templates(substitutions)
    elif argv[1] == 'on':
        update_pipeline_templates(argv[2:], substitutions)
    else:
        update_select_templates(argv[1:], substitutions)


if __name__ == '__main__':
    main()
