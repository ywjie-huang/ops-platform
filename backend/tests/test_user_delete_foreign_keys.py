from app.models.audit import AuditLog
from app.models.conversation import Conversation
from app.models.deploy import DeployApplication, DeployApproval, DeployRecord
from app.models.rbac import user_roles
from app.models.ticket import Ticket


def _single_fk_ondelete(table, column_name: str) -> str | None:
    foreign_keys = list(table.c[column_name].foreign_keys)
    assert len(foreign_keys) == 1
    return foreign_keys[0].ondelete


def test_user_history_foreign_keys_set_null_when_user_is_deleted():
    history_references = [
        (AuditLog.__table__, "user_id"),
        (Conversation.__table__, "user_id"),
        (DeployApplication.__table__, "creator_id"),
        (DeployRecord.__table__, "trigger_user_id"),
        (DeployApproval.__table__, "approver_id"),
        (Ticket.__table__, "creator_id"),
    ]

    for table, column_name in history_references:
        assert _single_fk_ondelete(table, column_name) == "SET NULL"


def test_user_role_join_rows_cascade_when_user_is_deleted():
    assert _single_fk_ondelete(user_roles, "user_id") == "CASCADE"


def test_startup_migration_covers_user_delete_foreign_keys():
    from app.db.init_db import USER_DELETE_CASCADE_FOREIGN_KEYS, USER_DELETE_SET_NULL_FOREIGN_KEYS

    assert {(table.name, column) for table, column in [
        (AuditLog.__table__, "user_id"),
        (Conversation.__table__, "user_id"),
        (DeployApplication.__table__, "creator_id"),
        (DeployRecord.__table__, "trigger_user_id"),
        (DeployApproval.__table__, "approver_id"),
        (Ticket.__table__, "creator_id"),
    ]} == {(table, column) for table, column, _, _ in USER_DELETE_SET_NULL_FOREIGN_KEYS}
    assert {("user_roles", "user_id")} == {
        (table, column) for table, column, _, _ in USER_DELETE_CASCADE_FOREIGN_KEYS
    }
