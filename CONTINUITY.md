Goal (criteria):
- Find a suitable 3D model/family for PK/fire hose sign or cabinet with high likelihood of fit for Revit use.

Constraints/Assumptions:
- Follow AGENTS.md: read/update CONTINUITY.md each turn; respond with Ledger Snapshot.
- Use TDD for new logic; tests must fail before implementation.
- Keep this file ASCII unless user requests Unicode headings/content.

Key decisions:
- Prefer Revit RFA families when available; otherwise identify high‑quality BIM sources with clear licensing.
- Keep the PK tool flexible: ViewBased annotation or point‑based model family.

State:
  - Done:
    - Added Place_Lights_PK tool (bundle + script) in Lighting panel.
    - Added pk_indicator_rules with tests.
    - Updated rules.default.json with PK keywords, height, dedupe, scan limits, and pk_indicator family type.
    - Web search for 3D candidates (Revit families and BIM objects) completed.
  - Now:
    - Recommend best 3D model options and confirm required format/category.
  - Next:
    - If user picks a source, download/load family and test in Revit.

Open questions (UNCONFIRMED if needed):
- UNCONFIRMED: Need Revit RFA (hosted/face-based) or any 3D format (FBX/OBJ)?
- UNCONFIRMED: Prefer PK sign only, or full fire hose cabinet model with sign?

Working set (files/ids/commands):
- CONTINUITY.md
- EOMTemplateTools.extension/lib/pk_indicator_rules.py
- tests/test_pk_indicator_rules.py
- EOMTemplateTools.extension/EOM.tab/02_Lighting.panel/Place_Lights_PK.pushbutton/script.py
- EOMTemplateTools.extension/EOM.tab/02_Lighting.panel/Place_Lights_PK.pushbutton/bundle.yaml
- EOMTemplateTools.extension/config/rules.default.json
