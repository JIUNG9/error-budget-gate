import json

import pytest

from budgetgate.cli import main


def run(*argv):
    return main(list(argv))


def test_allow_exits_0(capsys):
    code = run("--action", "rollout_restart", "--service", "checkout", "--budget", "0.8")
    assert code == 0
    assert capsys.readouterr().out.startswith("ALLOW")


def test_prod_requires_human_exits_10(capsys):
    code = run(
        "--action", "rollout_restart", "--service", "checkout", "--budget", "0.8", "--env", "prod"
    )
    assert code == 10
    assert capsys.readouterr().out.startswith("REQUIRE_HUMAN")


def test_irreversible_action_blocks_exits_20(capsys):
    code = run("--action", "delete_pvc", "--service", "checkout", "--budget", "0.8")
    assert code == 20
    assert "not a reversible" in capsys.readouterr().out


def test_exhausted_budget_blocks_exits_20():
    assert run("--action", "restart", "--service", "checkout", "--budget", "0") == 20


def test_tier0_in_prod_blocks_exits_20():
    code = run(
        "--action", "restart", "--service", "payments", "--budget", "0.9",
        "--env", "prod", "--tier", "0",
    )  # fmt: skip
    assert code == 20


def test_nan_budget_requires_human_exits_10():
    assert run("--action", "restart", "--service", "checkout", "--budget", "nan") == 10


def test_unknown_env_requires_human_exits_10():
    code = run("--action", "restart", "--service", "checkout", "--budget", "0.9", "--env", "prd")
    assert code == 10


def test_json_output(capsys):
    code = run("--action", "restart", "--service", "checkout", "--budget", "0.8", "--json")
    out = json.loads(capsys.readouterr().out)
    assert out["allow"] is True
    assert out["requires_human"] is False
    assert out["exit_code"] == code == 0


@pytest.mark.parametrize(
    "argv",
    [
        ["--service", "checkout", "--budget", "0.5"],
        ["--action", "restart", "--service", "checkout", "--budget", "lots"],
        ["--action", "restart", "--service", "checkout", "--budget", "0.5", "--tier", "9"],
    ],
)
def test_bad_arguments_exit_2(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


def test_non_prod_env_flag_opts_a_custom_env_in(capsys):
    code = run(
        "--action", "rollout_restart", "--service", "checkout", "--budget", "0.8",
        "--env", "preprod", "--non-prod-env", "preprod",
    )  # fmt: skip
    assert code == 0
    assert "env=preprod" in capsys.readouterr().out


def test_non_prod_env_flag_rejects_prod(capsys):
    with pytest.raises(SystemExit) as exc:
        run(
            "--action", "restart", "--service", "checkout", "--budget", "0.8",
            "--non-prod-env", "prod",
        )  # fmt: skip
    assert exc.value.code == 2
    assert "production" in capsys.readouterr().err
