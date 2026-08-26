"""
templates.py — Fokiz systemd and wrapper templates.
Copyright (C) Alenia Studios — GNU GPL v3
"""

from textwrap import dedent

# ---------------------------------------------------------------------------
# Unit templates
# ---------------------------------------------------------------------------

SERVICE_TEMPLATE = dedent("""\
    [Unit]
    Description=Fokiz Task Monitor and Procrastination Engine
    Documentation=https://github.com/Kaia-Alenia/fokiz
    After=network.target graphical-session.target

    [Service]
    Type=oneshot
    ExecStart={monitor_path}
    WorkingDirectory={script_dir}
    Environment=PYTHONUNBUFFERED=1
    StandardOutput=null
    StandardError=journal
""")

TIMER_TEMPLATE = dedent("""\
    [Unit]
    Description=Fokiz 1-Minute Evaluation Timer
    After=graphical-session.target

    [Timer]
    OnCalendar=*:*
    Persistent=true
    AccuracySec=10s

    [Install]
    WantedBy=timers.target
""")

# ---------------------------------------------------------------------------
# Wrapper templates
# ---------------------------------------------------------------------------

FOKIZ_WRAPPER_TEMPLATE = dedent("""\
    #!/usr/bin/env bash
    # Fokiz CLI wrapper
    FOKIZ_APP="{app_dir}"
    export PYTHONPATH="{script_dir}/src:$PYTHONPATH"
    exec {python_exec} -m app.cli "$@"
""")

MONITOR_WRAPPER_TEMPLATE = dedent("""\
    #!/usr/bin/env bash
    # Fokiz monitor wrapper
    FOKIZ_APP="{app_dir}"
    export PYTHONPATH="{script_dir}/src:$PYTHONPATH"
    exec {python_exec} "{monitor_py_path}" "$@"
""")
