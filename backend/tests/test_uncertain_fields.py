"""uncertain_fields 清洗测试。"""
from backend.app.services.structure_extractor import _sanitize_uncertain_fields
from backend.app.services.validation_engine import validate_structured


def test_sanitize_removes_omitted_organ_fields():
    structured = {
        "exam_type": "abdominal_ultrasound",
        "organs_examined": ["liver"],
        "liver": {
            "lesions": [
                {
                    "location": "右叶",
                    "size_mm": 30,
                    "echo": "hypoechoic",
                    "type": "solid",
                }
            ]
        },
        "metadata": {
            "uncertain_fields": [
                "liver.size",
                "liver.morphology",
                "liver.capsule",
                "gallbladder.size",
                "pancreas.echo",
            ],
        },
    }
    _sanitize_uncertain_fields(structured)
    assert structured["metadata"]["uncertain_fields"] == []


def test_sanitize_keeps_real_uncertain_lesion():
    structured = {
        "exam_type": "abdominal_ultrasound",
        "gallbladder": {
            "lesions": [
                {
                    "type": "polyp",
                    "size_mm": 4,
                    "uncertainty": True,
                }
            ]
        },
        "metadata": {
            "uncertain_fields": [
                "gallbladder.size",
                "gallbladder.lesions[0].size_mm",
            ],
        },
    }
    _sanitize_uncertain_fields(structured)
    fields = structured["metadata"]["uncertain_fields"]
    assert "gallbladder.size" not in fields
    assert "gallbladder.lesions[0]" in fields or "gallbladder.lesions[0].size_mm" in fields


def test_no_warning_after_sanitize_omitted():
    structured = {
        "exam_type": "abdominal_ultrasound",
        "liver": {"lesions": [{"size_mm": 30, "echo": "hypoechoic"}]},
        "metadata": {"uncertain_fields": []},
    }
    warnings = validate_structured(structured)
    assert "uncertainty_highlight" not in {w["id"] for w in warnings}
