from accounts.permission import ( 
    khusus_nasabah    as nasabah_only,
    khusus_teller     as teller_only,
    khusus_supervisor as supervisor_only,
    khusus_staf       as staff_only,
    registri_akses,
)

def role_required(*peran):
    return registri_akses.buat_dekorator(*peran)
