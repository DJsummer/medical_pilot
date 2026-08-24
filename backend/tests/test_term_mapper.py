"""术语映射测试。"""
from backend.app.services.report_generator import generate_report
from backend.app.services.term_mapper import humanize_location, humanize_term


def test_humanize_right_lobe():
    assert humanize_term("right_lobe") == "右叶"
    assert humanize_location("right_lobe", "肝") == "肝右叶"


def test_liver_report_no_english_location():
    data = {
        "exam_type": "abdominal_ultrasound",
        "organs_examined": ["liver", "gallbladder", "pancreas", "spleen"],
        "liver": {
            "lesions": [
                {
                    "location": "right_lobe",
                    "size_mm": 30,
                    "echo": "hypoechoic",
                    "type": "solid",
                    "boundary": "clear",
                }
            ]
        },
        "gallbladder": {"wall": {"status": "normal"}, "size": {"status": "normal"}},
        "pancreas": {"size": "normal", "duct_mm": 0},
        "spleen": {"size": {"status": "normal"}},
    }
    report = generate_report(data)
    assert "right_lobe" not in report["findings_text"]
    assert "右叶" in report["findings_text"]
    assert "低回声" in report["findings_text"]
