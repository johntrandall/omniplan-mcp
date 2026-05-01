#!/usr/bin/env python3
"""Build tests/fixtures/baseline.oplx from XML templates.

Minimal OmniPlan document bundle: one __test__root group task, no resources,
no dependencies. Tests create children under it and clean up `__test__*`
prefixed entities at teardown.

Run: python3 scripts/build-baseline-fixture.py

Re-run when:
  - The OmniPlan .oplx schema version changes (rare; tied to OmniPlan major).
  - The baseline contents need to change (e.g. add a calendar fixture).

The output is a directory bundle (UTI: com.omnigroup.omniplan2.planfile),
not a zip. OmniPlan accepts both forms via the .oplx extension.

See ~/.claude/skills/omniplan-format/SKILL.md for the canonical structure.
"""
from __future__ import annotations

import secrets
import shutil
import string
from pathlib import Path
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "baseline.oplx"

NS = "http://www.omnigroup.com/namespace/OmniPlan/v2"
ET.register_namespace("", NS)


def scenario_id() -> str:
    """11-char id, first char a lowercase letter, then base64-ish chars."""
    first = secrets.choice(string.ascii_lowercase)
    rest_chars = string.ascii_letters + string.digits + "-_"
    rest = "".join(secrets.choice(rest_chars) for _ in range(10))
    return first + rest


ACTUAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<scenario xmlns="{ns}" id="{scenario}">
  <start-date>2026-01-01T13:00:00.000Z</start-date>
  <granularity>hours</granularity>

  <prototype-task id="t-2"><type>task</type></prototype-task>
  <prototype-task id="t-3"><type>milestone</type></prototype-task>
  <prototype-task id="t-4"><type>group</type></prototype-task>
  <prototype-resource id="r-2"><type>Staff</type></prototype-resource>
  <prototype-resource id="r-3"><type>Equipment</type></prototype-resource>

  <top-resource idref="r-1"/>
  <resource id="r-1">
    <name/>
    <type>Group</type>
    <schedule>
      <schedule-day day-of-week="sunday"/>
      <schedule-day day-of-week="monday">
        <time-span start-time="28800" end-time="43200"/>
        <time-span start-time="46800" end-time="61200"/>
      </schedule-day>
      <schedule-day day-of-week="tuesday">
        <time-span start-time="28800" end-time="43200"/>
        <time-span start-time="46800" end-time="61200"/>
      </schedule-day>
      <schedule-day day-of-week="wednesday">
        <time-span start-time="28800" end-time="43200"/>
        <time-span start-time="46800" end-time="61200"/>
      </schedule-day>
      <schedule-day day-of-week="thursday">
        <time-span start-time="28800" end-time="43200"/>
        <time-span start-time="46800" end-time="61200"/>
      </schedule-day>
      <schedule-day day-of-week="friday">
        <time-span start-time="28800" end-time="43200"/>
        <time-span start-time="46800" end-time="61200"/>
      </schedule-day>
      <schedule-day day-of-week="saturday"/>
      <calendar name="Time Off" editable="yes" overtime="no"/>
      <calendar name="Overtime" editable="yes" overtime="yes"/>
    </schedule>
  </resource>

  <top-task idref="t-1"/>
  <task id="t-1">
    <title>Project</title>
    <type>group</type>
    <recalculate>duration</recalculate>
    <static-cost>0</static-cost>
    <child-task idref="t1"/>
  </task>
  <task id="t1">
    <title>__test__root</title>
    <type>group</type>
    <recalculate>duration</recalculate>
    <static-cost>0</static-cost>
  </task>

  <critical-path/>
</scenario>
"""


def toc_xml(scenario: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<omniplan xmlns="{NS}" file-format-version="3">
  <window>
    <editing-scenario>{scenario}</editing-scenario>
    <view>task</view>
    <task-view>
      <outline>
        <expanded-items idrefs="t-1 t1"/>
      </outline>
      <gantt-view/>
    </task-view>
    <resource-view>
      <outline/>
      <timeline/>
    </resource-view>
    <network-view/>
    <project-outline-view/>
  </window>
  <project>
    <next-task-id>2</next-task-id>
    <next-resource-id>2</next-resource-id>
    <scenario id="{scenario}" name="Actual" filename="Actual.xml"/>
    <date-display dates="true" times="true" seconds="false"/>
    <numbering-style>wbs</numbering-style>
    <auto-level/>
    <duration-format hours-per-day="8" hours-per-week="40" hours-per-month="160" hours-per-year="1920" hours="true" days="true" weeks="true"/>
    <effort-format hours-per-day="8" hours-per-week="40" hours-per-month="160" hours-per-year="1920" hours="true" days="true" weeks="true"/>
  </project>
</omniplan>
"""


CHANGELOG_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<changelog xmlns="{NS}">
  <version>4.0</version>
</changelog>
"""

PREVIEW_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c63606060600000000400015e7f6dba0000000049454e44"
    "ae426082"
)


def build() -> None:
    if FIXTURE_DIR.exists():
        shutil.rmtree(FIXTURE_DIR)
    FIXTURE_DIR.mkdir(parents=True)

    sc = scenario_id()
    (FIXTURE_DIR / "Actual.xml").write_text(ACTUAL_XML.format(ns=NS, scenario=sc))
    (FIXTURE_DIR / "__TOC.xml").write_text(toc_xml(sc))
    (FIXTURE_DIR / "__changelog.xml").write_text(CHANGELOG_XML)
    (FIXTURE_DIR / "Preview.png").write_bytes(PREVIEW_PNG_BYTES)

    for member in ("Actual.xml", "__TOC.xml", "__changelog.xml"):
        ET.parse(FIXTURE_DIR / member)

    print(f"Built {FIXTURE_DIR} (scenario={sc})")


if __name__ == "__main__":
    build()
