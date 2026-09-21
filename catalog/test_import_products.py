from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from catalog.models import Product

REQUIRED_HEADER = "id,title,description,price,location"


def _write_csv(path, body):
    path.write_text(body, encoding="utf-8")
    return str(path)


def test_wrong_header_count_aborts_immediately(db, tmp_path):
    path = _write_csv(
        tmp_path / "bad_count.csv",
        "id,title,description,price\n1,Sword,A sword,150\n",
    )
    with pytest.raises(CommandError, match=r"CSV header has 4 column\(s\), expected 5"):
        call_command("import_products", file=path)
    assert Product.objects.count() == 0


def test_wrong_header_names_aborts_immediately(db, tmp_path):
    path = _write_csv(
        tmp_path / "bad_names.csv",
        "id,name,description,price,location\n1,Sword,A sword,150,JO\n",
    )
    with pytest.raises(CommandError, match="does not match required columns"):
        call_command("import_products", file=path)
    assert Product.objects.count() == 0


def test_mixed_missing_values_are_logged_and_import_aborts(db, tmp_path):
    Product.objects.create(
        external_id=99,
        title="Keep Me",
        description="existing",
        price="1.00",
        location="JO",
    )
    path = _write_csv(
        tmp_path / "mixed.csv",
        "\n".join(
            [
                REQUIRED_HEADER,
                "1,Sword of Valor,A legendary sword,150,JO",
                "2,Shield of Aegis,,120,SA",
                "3,Potion of Healing,Restores health,20",
                "4,Mystic Wand,Casts spells, ,SA",
            ]
        )
        + "\n",
    )
    stderr = StringIO()
    with pytest.raises(CommandError, match=r"CSV validation failed: 3 row\(s\) have missing values"):
        call_command("import_products", file=path, stderr=stderr)

    logged = stderr.getvalue()
    assert "Row 3: missing values for columns: description" in logged
    assert "Row 4: expected 5 columns, found 4; missing values for: location" in logged
    assert "Row 5: missing values for columns: price" in logged
    assert Product.objects.count() == 1
    assert Product.objects.get(external_id=99).title == "Keep Me"


def test_valid_csv_imports_products(db, tmp_path):
    path = _write_csv(
        tmp_path / "ok.csv",
        "\n".join(
            [
                REQUIRED_HEADER,
                "1,Sword of Valor,A legendary sword,150,JO",
                "2,Shield of Aegis,An indestructible shield,120.50,SA",
            ]
        )
        + "\n",
    )
    call_command("import_products", file=path)
    assert Product.objects.count() == 2
    sword = Product.objects.get(external_id=1)
    assert sword.title == "Sword of Valor"
    assert sword.description == "A legendary sword"
    assert str(sword.price) == "150.00"
    assert sword.location == "JO"
