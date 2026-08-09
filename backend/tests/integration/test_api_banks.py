"""Banka uçlarının testleri."""

from __future__ import annotations

import httpx


class TestBankaListesi:
    def test_tum_bankalar_donuyor(self, api_client: httpx.Client) -> None:
        yanit = api_client.get("/api/v1/banks")
        assert yanit.status_code == 200
        assert len(yanit.json()) == 10

    def test_kapsam_disi_banka_listede_yok(self, api_client: httpx.Client) -> None:
        """İktisat Katılım proje kapsamı dışındadır."""
        kodlar = {b["code"] for b in api_client.get("/api/v1/banks").json()}
        assert "iktisat_katilim" not in kodlar

    def test_kampanyasiz_bankalar_listede_kalir(self, api_client: httpx.Client) -> None:
        """⚠️ Kampanya sayfası olmayan banka listeden ÇIKARILMAZ.

        Adil Katılım'ın kamuya açık kampanya sayfası yok; kayıt 0 ile döner.
        "Veri yok" bilgisi de başlı başına bir bulgudur.
        """
        bankalar = {b["code"]: b for b in api_client.get("/api/v1/banks").json()}

        assert bankalar["adil_katilim"]["campaign_count"] == 0
        assert bankalar["adil_katilim"]["data_status"] == "none"

    def test_veri_yoklugunun_gerekcesi_belgelenmis(self, api_client: httpx.Client) -> None:
        bankalar = {b["code"]: b for b in api_client.get("/api/v1/banks").json()}
        assert bankalar["adil_katilim"]["notes"]
        assert "kampanya" in bankalar["adil_katilim"]["notes"].lower()


class TestBankaDetayi:
    def test_banka_detayi(self, api_client: httpx.Client) -> None:
        yanit = api_client.get("/api/v1/banks/emlak_katilim")
        assert yanit.status_code == 200

        veri = yanit.json()
        assert veri["name"] == "Türkiye Emlak Katılım"
        assert veri["website"] == "https://www.emlakkatilim.com.tr"
        assert veri["legacy_domains"] == ["emlakbank.com.tr"]

    def test_olmayan_banka_404_ve_hata_zarfi(self, api_client: httpx.Client) -> None:
        yanit = api_client.get("/api/v1/banks/olmayan_banka")
        assert yanit.status_code == 404

        gövde = yanit.json()
        assert gövde["error"]["code"] == "NOT_FOUND"
        assert "bulunamadı" in gövde["error"]["message"].lower()
