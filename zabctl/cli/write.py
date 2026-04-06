"""
zabctl write commands.

Verbs: enable, disable, acknowledge, maintenance, create, delete.
All destructive commands prompt for confirmation unless --yes/-y is given.
Write commands always emit a human-readable summary to stderr even in json mode.
"""

from __future__ import annotations

from typing import Any

import click
import yaml

from zabctl.api.resources import events, hosts, maintenance, triggers, usergroups, users
from zabctl.api.utils import parse_time
from zabctl.cli._common import _handle_api_error, _make_client, _resolve_output
from zabctl.config.loader import ZabctlConfig
from zabctl.output.formatter import format_output


def _write_output(
    result: dict[str, Any],
    *,
    fmt: str,
    command: str,
    cfg: ZabctlConfig,
    client: Any,
    columns: list[str],
) -> None:
    format_output(
        data=[result],
        output_format=fmt,
        command=command,
        server=cfg.server,
        api_version=client.api_version,
        columns=columns,
    )


# ---------------------------------------------------------------------------
# zabctl enable
# ---------------------------------------------------------------------------

@click.group("enable")
def enable() -> None:
    """Enable a Zabbix resource."""


@enable.command("host")
@click.argument("id_or_name")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def enable_host(cfg: ZabctlConfig, id_or_name: str, output: str | None) -> None:
    """Enable monitoring for a host (sets status=0)."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        result = hosts.enable_host(client, id_or_name)
    except Exception as exc:
        _handle_api_error(exc)
        return
    click.echo(f"enabled host {id_or_name!r} → hostids: {result.get('hostids')}", err=True)
    _write_output(result, fmt=fmt, command="enable host", cfg=cfg, client=client, columns=["hostids"])


@enable.command("trigger")
@click.argument("trigger_id")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def enable_trigger(cfg: ZabctlConfig, trigger_id: str, output: str | None) -> None:
    """Enable a trigger (sets status=0)."""
    if not trigger_id.isdigit():
        click.echo(f"error: trigger id must be numeric, got: {trigger_id!r}", err=True)
        raise SystemExit(5)
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        result = triggers.enable_trigger(client, trigger_id)
    except Exception as exc:
        _handle_api_error(exc)
        return
    click.echo(f"enabled trigger {trigger_id!r} → triggerids: {result.get('triggerids')}", err=True)
    _write_output(result, fmt=fmt, command="enable trigger", cfg=cfg, client=client, columns=["triggerids"])


# ---------------------------------------------------------------------------
# zabctl disable
# ---------------------------------------------------------------------------

@click.group("disable")
def disable() -> None:
    """Disable a Zabbix resource."""


@disable.command("host")
@click.argument("id_or_name")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def disable_host(cfg: ZabctlConfig, id_or_name: str, output: str | None) -> None:
    """Disable monitoring for a host (sets status=1)."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        result = hosts.disable_host(client, id_or_name)
    except Exception as exc:
        _handle_api_error(exc)
        return
    click.echo(f"disabled host {id_or_name!r} → hostids: {result.get('hostids')}", err=True)
    _write_output(result, fmt=fmt, command="disable host", cfg=cfg, client=client, columns=["hostids"])


@disable.command("trigger")
@click.argument("trigger_id")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def disable_trigger(cfg: ZabctlConfig, trigger_id: str, output: str | None) -> None:
    """Disable a trigger (sets status=1)."""
    if not trigger_id.isdigit():
        click.echo(f"error: trigger id must be numeric, got: {trigger_id!r}", err=True)
        raise SystemExit(5)
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        result = triggers.disable_trigger(client, trigger_id)
    except Exception as exc:
        _handle_api_error(exc)
        return
    click.echo(f"disabled trigger {trigger_id!r} → triggerids: {result.get('triggerids')}", err=True)
    _write_output(result, fmt=fmt, command="disable trigger", cfg=cfg, client=client, columns=["triggerids"])


# ---------------------------------------------------------------------------
# zabctl acknowledge <event-id>
# ---------------------------------------------------------------------------

@click.command("acknowledge")
@click.argument("event_id")
@click.option("--message", "-m", default=None, help="Message to attach to the action.")
@click.option("--close", is_flag=True, default=False, help="Close the problem.")
@click.option("--suppress", is_flag=True, default=False, help="Suppress the problem.")
@click.option("--unsuppress", is_flag=True, default=False, help="Unsuppress (un-suppress) the problem.")
@click.option("--unacknowledge", is_flag=True, default=False, help="Remove acknowledgment from the problem.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def acknowledge(
    cfg: ZabctlConfig,
    event_id: str,
    message: str | None,
    close: bool,
    suppress: bool,
    unsuppress: bool,
    unacknowledge: bool,
    output: str | None,
) -> None:
    """Acknowledge, close, suppress, unsuppress, or unacknowledge a problem event.

    \b
    Examples:
      zabctl acknowledge 42 --message "Investigating"
      zabctl acknowledge 42 --close --message "Fixed"
      zabctl acknowledge 42 --suppress
      zabctl acknowledge 42 --unsuppress
      zabctl acknowledge 42 --unacknowledge
    """
    exclusive = sum([suppress, unsuppress, unacknowledge])
    if exclusive > 1:
        click.echo("error: --suppress, --unsuppress, --unacknowledge are mutually exclusive", err=True)
        raise SystemExit(5)

    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        result = events.acknowledge_event(
            client,
            event_id,
            message=message,
            close=close,
            suppress=suppress,
            unsuppress=unsuppress,
            unacknowledge=unacknowledge,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return

    if suppress:
        action_label = "suppressed"
    elif unsuppress:
        action_label = "unsuppressed"
    elif unacknowledge:
        action_label = "unacknowledged"
    elif close:
        action_label = "acknowledged+closed"
    else:
        action_label = "acknowledged"
    click.echo(f"{action_label} event {event_id!r} → eventids: {result.get('eventids')}", err=True)
    _write_output(result, fmt=fmt, command="acknowledge", cfg=cfg, client=client, columns=["eventids"])


# ---------------------------------------------------------------------------
# zabctl maintenance
# ---------------------------------------------------------------------------

@click.group("maintenance")
def maintenance_group() -> None:
    """Manage Zabbix maintenance windows."""


@maintenance_group.command("create")
@click.option("--host", "host_names", multiple=True, required=True, help="Host name(s) to include (repeatable).")
@click.option("--start", required=True, help="Start time (ISO 8601, e.g. 2026-04-01T02:00:00, or Unix epoch).")
@click.option("--duration", required=True, type=int, help="Duration in minutes.")
@click.option("--name", default=None, help="Maintenance window name (auto-generated if omitted).")
@click.option("--no-data", is_flag=True, default=False, help="Suppress data collection during maintenance.")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def maintenance_create(
    cfg: ZabctlConfig,
    host_names: tuple[str, ...],
    start: str,
    duration: int,
    name: str | None,
    no_data: bool,
    yes: bool,
    output: str | None,
) -> None:
    """Create a maintenance window for one or more hosts."""
    try:
        start_epoch = parse_time(start)
    except ValueError as exc:
        click.echo(f"error: {exc}", err=True)
        raise SystemExit(5)

    window_name = name or f"zabctl {','.join(host_names)} {start}"
    fmt = _resolve_output(cfg.output, output)

    if not yes:
        click.confirm(
            f"Create maintenance {window_name!r} for {list(host_names)} starting {start} ({duration} min)?",
            abort=True,
        )

    client = _make_client(cfg)

    # Resolve host names to IDs.
    host_ids: list[str] = []
    for h in host_names:
        try:
            hid = hosts._resolve_hostid(client, h)
            host_ids.append(hid)
        except Exception as exc:
            _handle_api_error(exc)
            return

    try:
        result = maintenance.create_maintenance(
            client,
            name=window_name,
            host_ids=host_ids,
            start_epoch=start_epoch,
            duration_minutes=duration,
            no_data=no_data,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return

    click.echo(
        f"created maintenance {window_name!r} → maintenanceids: {result.get('maintenanceids')}",
        err=True,
    )
    _write_output(result, fmt=fmt, command="maintenance create", cfg=cfg, client=client, columns=["maintenanceids"])


@maintenance_group.command("delete")
@click.argument("maintenance_id")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def maintenance_delete(
    cfg: ZabctlConfig,
    maintenance_id: str,
    yes: bool,
    output: str | None,
) -> None:
    """Delete a maintenance window by id."""
    if not yes:
        click.confirm(f"Delete maintenance {maintenance_id!r}? This cannot be undone.", abort=True)
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        result = maintenance.delete_maintenance(client, maintenance_id)
    except Exception as exc:
        _handle_api_error(exc)
        return
    click.echo(f"deleted maintenance {maintenance_id!r} → maintenanceids: {result.get('maintenanceids')}", err=True)
    _write_output(result, fmt=fmt, command="maintenance delete", cfg=cfg, client=client, columns=["maintenanceids"])


# ---------------------------------------------------------------------------
# zabctl create
# ---------------------------------------------------------------------------

@click.group("create")
def create_group() -> None:
    """Create Zabbix resources."""


@create_group.command("host")
@click.option("--from-file", "from_file", default=None, type=click.Path(exists=True), help="YAML file describing the host.")
@click.option("--host", "host_name", default=None, help="Host technical name.")
@click.option("--group", "group_names", multiple=True, help="Host group name(s) (repeatable).")
@click.option("--template", "template_names", multiple=True, help="Template name(s) to link (repeatable).")
@click.option("--ip", default="127.0.0.1", show_default=True, help="Agent interface IP address.")
@click.option("--port", default="10050", show_default=True, help="Agent interface port.")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def create_host(
    cfg: ZabctlConfig,
    from_file: str | None,
    host_name: str | None,
    group_names: tuple[str, ...],
    template_names: tuple[str, ...],
    ip: str,
    port: str,
    yes: bool,
    output: str | None,
) -> None:
    """Create a Zabbix host. Provide either --from-file or --host + --group."""
    if from_file and host_name:
        click.echo("error: --from-file and --host are mutually exclusive", err=True)
        raise SystemExit(5)
    if not from_file and not host_name:
        click.echo("error: provide --from-file or --host", err=True)
        raise SystemExit(5)
    if not from_file and not group_names:
        click.echo("error: --group is required when using --host", err=True)
        raise SystemExit(5)

    fmt = _resolve_output(cfg.output, output)

    if not yes:
        label = from_file or host_name
        click.confirm(f"Create host {label!r}?", abort=True)

    client = _make_client(cfg)
    try:
        if from_file:
            result = hosts.create_host_from_file(client, from_file)
        else:
            result = hosts.create_host(
                client,
                host=host_name,  # type: ignore[arg-type]
                group_names=list(group_names),
                interface_ip=ip,
                interface_port=port,
                template_names=list(template_names) if template_names else None,
            )
    except Exception as exc:
        _handle_api_error(exc)
        return

    label = from_file or host_name
    click.echo(f"created host {label!r} → hostids: {result.get('hostids')}", err=True)
    _write_output(result, fmt=fmt, command="create host", cfg=cfg, client=client, columns=["hostids"])


@create_group.command("user")
@click.option("--username", required=True, help="Login username.")
@click.option("--password", required=True, hide_input=True, help="Initial password.")
@click.option("--role", "role_name", required=True, help="Role name or numeric roleid.")
@click.option("--group", "group_names", multiple=True, required=True, help="User group name(s) (repeatable).")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def create_user(
    cfg: ZabctlConfig,
    username: str,
    password: str,
    role_name: str,
    group_names: tuple[str, ...],
    yes: bool,
    output: str | None,
) -> None:
    """Create a Zabbix user.

    \b
    Examples:
      zabctl create user --username alice --password s3cr3t --role "Zabbix User" --group "Linux Team"
      zabctl create user --username bob --password s3cr3t --role 1 --group "Zabbix administrators" --yes
    """
    if username in users._PROTECTED_USERNAMES:
        click.echo(f"error: cannot create user with protected username {username!r}", err=True)
        raise SystemExit(5)

    fmt = _resolve_output(cfg.output, output)

    if not yes:
        click.confirm(f"Create user {username!r} with role {role_name!r} in groups {list(group_names)}?", abort=True)

    client = _make_client(cfg)

    # Resolve role name → id.
    try:
        role = users.get_role_by_name(client, role_name)
    except Exception as exc:
        _handle_api_error(exc)
        return

    # Resolve group names → ids.
    group_ids: list[str] = []
    for gname in group_names:
        try:
            grp = usergroups.get_usergroup(client, gname)
            group_ids.append(grp["usrgrpid"])
        except Exception as exc:
            _handle_api_error(exc)
            return

    try:
        result = users.create_user(
            client,
            username=username,
            password=password,
            roleid=role["roleid"],
            group_ids=group_ids,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return

    click.echo(f"created user {username!r} → userids: {result.get('userids')}", err=True)
    _write_output(result, fmt=fmt, command="create user", cfg=cfg, client=client, columns=["userids"])


@create_group.command("usergroup")
@click.option("--name", required=True, help="User group name.")
@click.option(
    "--gui-access",
    "gui_access",
    default="default",
    show_default=True,
    type=click.Choice(["default", "internal", "ldap", "disable"]),
    help="Frontend access method.",
)
@click.option("--disabled", is_flag=True, default=False, help="Create the group in disabled state.")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def create_usergroup(
    cfg: ZabctlConfig,
    name: str,
    gui_access: str,
    disabled: bool,
    yes: bool,
    output: str | None,
) -> None:
    """Create a Zabbix user group.

    \b
    Examples:
      zabctl create usergroup --name "Linux Team"
      zabctl create usergroup --name "Read-Only" --gui-access internal --disabled
    """
    _GUI_ACCESS_MAP = {"default": 0, "internal": 1, "ldap": 2, "disable": 3}
    gui_access_val = _GUI_ACCESS_MAP[gui_access]
    users_status_val = 1 if disabled else 0

    fmt = _resolve_output(cfg.output, output)

    if not yes:
        click.confirm(f"Create user group {name!r}?", abort=True)

    client = _make_client(cfg)
    try:
        result = usergroups.create_usergroup(
            client,
            name=name,
            gui_access=gui_access_val,
            users_status=users_status_val,
        )
    except Exception as exc:
        _handle_api_error(exc)
        return

    click.echo(f"created usergroup {name!r} → usrgrpids: {result.get('usrgrpids')}", err=True)
    _write_output(result, fmt=fmt, command="create usergroup", cfg=cfg, client=client, columns=["usrgrpids"])


# ---------------------------------------------------------------------------
# zabctl tag / untag
# ---------------------------------------------------------------------------

@click.group("tag")
def tag_group() -> None:
    """Add tags to Zabbix resources."""


@tag_group.command("host")
@click.argument("id_or_name")
@click.option("--tag", "tag_name", required=True, metavar="NAME", help="Tag name.")
@click.option("--value", "tag_value", default="", show_default=True, help="Tag value (default: empty string).")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def tag_host(cfg: ZabctlConfig, id_or_name: str, tag_name: str, tag_value: str, output: str | None) -> None:
    """Add a tag to a host (merges with existing tags).

    \b
    Example:
      zabctl tag host web01 --tag env --value production
      zabctl tag host web01 --tag managed-by
    """
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        result = hosts.add_host_tag(client, id_or_name, tag=tag_name, value=tag_value)
    except Exception as exc:
        _handle_api_error(exc)
        return
    click.echo(f"tagged host {id_or_name!r} with {tag_name!r}={tag_value!r} → hostids: {result.get('hostids')}", err=True)
    _write_output(result, fmt=fmt, command="tag host", cfg=cfg, client=client, columns=["hostids"])


@click.group("untag")
def untag_group() -> None:
    """Remove tags from Zabbix resources."""


@untag_group.command("host")
@click.argument("id_or_name")
@click.option("--tag", "tag_name", required=True, metavar="NAME", help="Tag name to remove.")
@click.option("--value", "tag_value", default=None, help="Remove only this specific tag+value pair (omit to remove all tags with this name).")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def untag_host(cfg: ZabctlConfig, id_or_name: str, tag_name: str, tag_value: str | None, output: str | None) -> None:
    """Remove a tag from a host.

    \b
    Example:
      zabctl untag host web01 --tag env --value production
      zabctl untag host web01 --tag env   # removes all tags named 'env'
    """
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        result = hosts.remove_host_tag(client, id_or_name, tag=tag_name, value=tag_value)
    except Exception as exc:
        _handle_api_error(exc)
        return
    msg = f"removed tag {tag_name!r}"
    if tag_value is not None:
        msg += f"={tag_value!r}"
    click.echo(f"{msg} from host {id_or_name!r} → hostids: {result.get('hostids')}", err=True)
    _write_output(result, fmt=fmt, command="untag host", cfg=cfg, client=client, columns=["hostids"])


# ---------------------------------------------------------------------------
# zabctl delete
# ---------------------------------------------------------------------------

@click.group("delete")
def delete_group() -> None:
    """Delete Zabbix resources."""


@delete_group.command("host")
@click.argument("id_or_name")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def delete_host(cfg: ZabctlConfig, id_or_name: str, yes: bool, output: str | None) -> None:
    """Delete a host. Prompts for confirmation unless --yes is given."""
    if not yes:
        click.confirm(f"Delete host {id_or_name!r}? This cannot be undone.", abort=True)
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)
    try:
        result = hosts.delete_host(client, id_or_name)
    except Exception as exc:
        _handle_api_error(exc)
        return
    click.echo(f"deleted host {id_or_name!r} → hostids: {result.get('hostids')}", err=True)
    _write_output(result, fmt=fmt, command="delete host", cfg=cfg, client=client, columns=["hostids"])


@delete_group.command("user")
@click.argument("id_or_name")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def delete_user(cfg: ZabctlConfig, id_or_name: str, yes: bool, output: str | None) -> None:
    """Delete a user by userid or username. Prompts for confirmation unless --yes is given."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)

    # Resolve user first so we can show the username in the prompt and run hardblock checks.
    try:
        user_record = users.get_user(client, id_or_name)
    except Exception as exc:
        _handle_api_error(exc)
        return

    target_username = user_record.get("username", "")

    # Hardblock: never delete Admin.
    if target_username in users._PROTECTED_USERNAMES:
        click.echo(f"error: {target_username!r} is a protected account and cannot be deleted", err=True)
        raise SystemExit(5)

    # Hardblock: never delete the token-owner.
    current = client.current_user_info()
    if current and current.get("username") == target_username:
        click.echo(f"error: cannot delete the currently authenticated user {target_username!r}", err=True)
        raise SystemExit(5)

    if not yes:
        click.confirm(f"Delete user {target_username!r} (userid={user_record['userid']})? This cannot be undone.", abort=True)

    try:
        result = users.delete_user(client, user_record["userid"])
    except Exception as exc:
        _handle_api_error(exc)
        return

    click.echo(f"deleted user {target_username!r} → userids: {result.get('userids') or result}", err=True)
    _write_output(
        {"userids": result} if isinstance(result, list) else result,
        fmt=fmt,
        command="delete user",
        cfg=cfg,
        client=client,
        columns=["userids"],
    )


@delete_group.command("usergroup")
@click.argument("id_or_name")
@click.option("--yes", "-y", is_flag=True, default=False, help="Skip confirmation prompt.")
@click.option("--output", "-o", default=None, type=click.Choice(["table", "json", "jsonl", "yaml", "wide"]))
@click.pass_obj
def delete_usergroup(cfg: ZabctlConfig, id_or_name: str, yes: bool, output: str | None) -> None:
    """Delete a user group by id or name. Prompts for confirmation unless --yes is given."""
    fmt = _resolve_output(cfg.output, output)
    client = _make_client(cfg)

    # Resolve group first so we can show the name in the confirmation prompt.
    try:
        group_record = usergroups.get_usergroup(client, id_or_name)
    except Exception as exc:
        _handle_api_error(exc)
        return

    group_name = group_record.get("name", id_or_name)

    if not yes:
        click.confirm(f"Delete user group {group_name!r} (usrgrpid={group_record['usrgrpid']})? This cannot be undone.", abort=True)

    try:
        result = usergroups.delete_usergroup(client, group_record["usrgrpid"])
    except Exception as exc:
        _handle_api_error(exc)
        return

    click.echo(f"deleted usergroup {group_name!r} → usrgrpids: {result.get('usrgrpids') or result}", err=True)
    _write_output(
        {"usrgrpids": result} if isinstance(result, list) else result,
        fmt=fmt,
        command="delete usergroup",
        cfg=cfg,
        client=client,
        columns=["usrgrpids"],
    )
