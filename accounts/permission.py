from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


class IzinAkses:
    def __init__(self):
        self._daftar_peran: set[str] = set()
        self._pesan_tolak = 'Anda tidak memiliki akses ke halaman ini.'
        self._url_login = 'accounts:login'
        self._url_dasbor = 'accounts:dashboard'

    def daftarkan(self, *peran: str) -> 'IzinAkses':
        for p in peran:
            self._daftar_peran.add(p)
        return self

    def peran_terdaftar(self) -> frozenset:
        return frozenset(self._daftar_peran)

    def buat_dekorator(self, *peran_diizinkan: str):
        for p in peran_diizinkan:
            if p not in self._daftar_peran:
                raise ValueError(
                    f"Peran '{p}' belum didaftarkan di IzinAkses. "
                    f"Panggil .daftarkan('{p}') terlebih dahulu."
                )

        def dekorator(fungsi_view):
            @wraps(fungsi_view)
            def _pembungkus(request, *args, **kwargs):
                if not request.user.is_authenticated:
                    return redirect(self._url_login)
                if request.user.role not in peran_diizinkan:
                    messages.error(request, self._pesan_tolak)
                    return redirect(self._url_dasbor)
                return fungsi_view(request, *args, **kwargs)
            return _pembungkus
        return dekorator

    def buat_dekorator_gabungan(self, *peran_diizinkan: str):
        return self.buat_dekorator(*peran_diizinkan)

registri_akses = IzinAkses()
registri_akses.daftarkan('nasabah', 'teller', 'supervisor')

khusus_nasabah    = registri_akses.buat_dekorator('nasabah')
khusus_teller     = registri_akses.buat_dekorator('teller')
khusus_supervisor = registri_akses.buat_dekorator('supervisor')
khusus_staf       = registri_akses.buat_dekorator_gabungan('teller', 'supervisor')
