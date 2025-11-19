from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget

from win_llm_chat_pyside.features.attachments.attachment_widgets import AttachmentListWidget
from win_llm_chat_pyside.models import AttachmentMetadata


def _sample_attachment(index: int) -> AttachmentMetadata:
    return AttachmentMetadata(
        id=f"att-{index}",
        session_id="sess-1",
        filename=f"sample-{index}.txt",
        size_bytes=1024,
        mime_type="text/plain",
        status="ready",
    )


def test_focus_preferred_item_selects_first_when_none(qt_app):  # noqa: ARG001
    widget = AttachmentListWidget()
    widget.show()
    widget.raise_()
    widget.activateWindow()
    attachments = [_sample_attachment(1), _sample_attachment(2)]
    widget.set_attachments(attachments)

    assert widget.current_attachment_id() is None

    widget.focus_preferred_item()

    assert widget.current_attachment_id() == "att-1"
    tree = widget.findChild(QTreeWidget)
    assert tree is not None
    assert tree.currentItem() is not None


def test_selected_attachment_ids_updates_with_checkboxes(qt_app):  # noqa: ARG001
    widget = AttachmentListWidget()
    attachments = [_sample_attachment(1), _sample_attachment(2), _sample_attachment(3)]
    widget.set_attachments(attachments)

    tree = widget.findChild(QTreeWidget)
    assert tree is not None

    first_item = tree.topLevelItem(0)
    second_item = tree.topLevelItem(1)
    assert first_item is not None
    assert second_item is not None

    first_item.setCheckState(0, Qt.Checked)
    assert widget.selected_attachment_ids() == ["att-1"]

    second_item.setCheckState(0, Qt.Checked)
    assert widget.selected_attachment_ids() == ["att-1", "att-2"]

    widget.clear_send_selection()
    assert widget.selected_attachment_ids() == []

    # Ensure selections referencing removed attachments are dropped
    first_item.setCheckState(0, Qt.Checked)
    widget.set_attachments(attachments[1:])
    assert "att-1" not in widget.selected_attachment_ids()


