from datetime import timedelta

from glosa_core.domain import AccessToken, ActorKind, Credentials, Scope
from glosa_core.testing import FixedClock
from glosa_core.tokens import TOKEN_PREFIX, TokenAuthenticator, generate_token, hash_token

from conftest import COL_A


def make_token(access, raw, **overrides):
    data = dict(
        id="tok-1",
        collection_id=COL_A,
        created_by="ana",
        hash=hash_token(raw),
        scopes=frozenset({Scope.READ}),
    )
    data.update(overrides)
    access.save_token(AccessToken(**data))


def test_el_token_tiene_prefijo_y_el_hash_no_es_el_valor():
    raw = generate_token()
    assert raw.startswith(TOKEN_PREFIX)
    assert hash_token(raw) != raw
    assert hash_token(raw) == hash_token(raw)
    assert generate_token() != raw


def test_token_valido_identifica_al_actor(access, clock):
    raw = generate_token()
    make_token(access, raw)
    actor = TokenAuthenticator(access, clock).identify(Credentials(raw))
    assert actor is not None
    assert actor.kind is ActorKind.TOKEN
    assert actor.collection_id == COL_A
    assert actor.scopes == frozenset({Scope.READ})


def test_token_revocado_se_rechaza_de_inmediato(access, clock):  # prueba obligatoria 3
    raw = generate_token()
    make_token(access, raw)
    auth = TokenAuthenticator(access, clock)
    assert auth.identify(Credentials(raw)) is not None
    access.revoke_token("tok-1")
    assert auth.identify(Credentials(raw)) is None


def test_token_caducado_se_rechaza(access):  # prueba obligatoria 3
    clock = FixedClock()
    raw = generate_token()
    make_token(access, raw, expires_at=clock.now() + timedelta(hours=1))
    auth = TokenAuthenticator(access, clock)
    assert auth.identify(Credentials(raw)) is not None
    clock.advance(hours=2)
    assert auth.identify(Credentials(raw)) is None


def test_credenciales_invalidas(access, clock):
    auth = TokenAuthenticator(access, clock)
    assert auth.identify(Credentials(None)) is None
    assert auth.identify(Credentials("")) is None
    assert auth.identify(Credentials("sin-prefijo")) is None
    assert auth.identify(Credentials(TOKEN_PREFIX + "desconocido")) is None
