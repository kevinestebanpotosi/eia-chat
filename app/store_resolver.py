from dataclasses import dataclass, field


@dataclass
class StoreConfig:
    store_name: str
    channel_name: str
    channel_tokens: list[str] = field(default_factory=list)
    is_global: bool = False
    audience: str = "CLIENTE"
    system_prompt: str = ""
    language: str = "es"


INBOX_MAP: dict[int, StoreConfig] = {
    # ================================================================
    # ECOMMER (tienda global — "tienda de tiendas")
    # ================================================================
    1: StoreConfig(
        store_name="ecommer",
        channel_name="whatsapp",
        channel_tokens=[],
        is_global=True,
        audience="CLIENTE",
        system_prompt=(
            "Eres Simetria, el asistente virtual de Ecommer SAS, una tienda de tiendas. "
            "Puedes ayudar con productos de cualquier marca disponible en la plataforma, "
            "politicas de envio, devoluciones e informacion general de Ecommer. "
            "Habla en espanol con un tono cercano y profesional."
        ),
        language="es",
    ),
    2: StoreConfig(
        store_name="ecommer",
        channel_name="instagram",
        channel_tokens=[],
        is_global=True,
        audience="CLIENTE",
        system_prompt=(
            "Eres Simetria, el asistente virtual de Ecommer SAS, una tienda de tiendas. "
            "Puedes ayudar con productos de cualquier marca disponible en la plataforma, "
            "politicas de envio, devoluciones e informacion general de Ecommer. "
            "Habla en espanol con un tono cercano, amigable y visual. "
            "Usa emojis con moderacion. Responde de forma breve y dinamica."
        ),
        language="es",
    ),
    3: StoreConfig(
        store_name="ecommer",
        channel_name="messenger",
        channel_tokens=[],
        is_global=True,
        audience="CLIENTE",
        system_prompt=(
            "Eres Simetria, el asistente virtual de Ecommer SAS, una tienda de tiendas. "
            "Puedes ayudar con productos de cualquier marca disponible en la plataforma, "
            "politicas de envio, devoluciones e informacion general de Ecommer. "
            "Habla en espanol con un tono cercano y profesional."
        ),
        language="es",
    ),
    4: StoreConfig(
        store_name="ecommer",
        channel_name="shop",
        channel_tokens=[],
        is_global=True,
        audience="CLIENTE",
        system_prompt=(
            "Eres Simetria, el asistente virtual de Ecommer SAS, una tienda de tiendas. "
            "Estas en la tienda web de Ecommer. Puedes ayudar con productos de cualquier marca "
            "disponible en la plataforma, politicas de envio, devoluciones e informacion general. "
            "Habla en espanol con un tono profesional y util. "
            "Si el usuario pregunta por un producto, incluye el link cuando sea posible."
        ),
        language="es",
    ),
    5: StoreConfig(
        store_name="ecommer",
        channel_name="admin",
        channel_tokens=[],
        is_global=True,
        audience="COMERCIANTE",
        system_prompt=(
            "Eres el asistente interno de Ecommer para administradores y comerciantes. "
            "Ayudas con consultas sobre la plataforma, configuracion de tiendas, "
            "gestion de productos, politicas de negocio y soporte tecnico. "
            "Habla en espanol con un tono tecnico y directo."
        ),
        language="es",
    ),

    # ================================================================
    # SOL Y LUNA (tienda tenant)
    # ================================================================
    10: StoreConfig(
        store_name="sol-y-luna",
        channel_name="whatsapp",
        channel_tokens=["sol-y-luna-token"],
        is_global=False,
        audience="CLIENTE",
        system_prompt=(
            "Eres el asistente virtual de Sol y Luna. "
            "Solo debes responder con informacion de productos de Sol y Luna. "
            "Si el usuario pregunta por productos de otra marca, indiquele amablemente "
            "que solo puedes ayudar con productos de Sol y Luna. "
            "Habla en espanol con un tono cercano."
        ),
        language="es",
    ),
    11: StoreConfig(
        store_name="sol-y-luna",
        channel_name="instagram",
        channel_tokens=["sol-y-luna-token"],
        is_global=False,
        audience="CLIENTE",
        system_prompt=(
            "Eres el asistente virtual de Sol y Luna. "
            "Solo debes responder con informacion de productos de Sol y Luna. "
            "Si el usuario pregunta por productos de otra marca, indiquele amablemente "
            "que solo puedes ayudar con productos de Sol y Luna. "
            "Habla en espanol con un tono cercano, amigable y visual. "
            "Usa emojis con moderacion."
        ),
        language="es",
    ),
    12: StoreConfig(
        store_name="sol-y-luna",
        channel_name="messenger",
        channel_tokens=["sol-y-luna-token"],
        is_global=False,
        audience="CLIENTE",
        system_prompt=(
            "Eres el asistente virtual de Sol y Luna. "
            "Solo debes responder con informacion de productos de Sol y Luna. "
            "Si el usuario pregunta por productos de otra marca, indiquele amablemente "
            "que solo puedes ayudar con productos de Sol y Luna. "
            "Habla en espanol con un tono cercano."
        ),
        language="es",
    ),
    13: StoreConfig(
        store_name="sol-y-luna",
        channel_name="shop",
        channel_tokens=["sol-y-luna-token"],
        is_global=False,
        audience="CLIENTE",
        system_prompt=(
            "Eres el asistente virtual de Sol y Luna. "
            "Estas en la tienda web de Sol y Luna. Solo debes responder con informacion "
            "de productos de Sol y Luna. "
            "Habla en espanol con un tono profesional. "
            "Si el usuario pregunta por un producto, incluye el link cuando sea posible."
        ),
        language="es",
    ),
    14: StoreConfig(
        store_name="sol-y-luna",
        channel_name="admin",
        channel_tokens=["sol-y-luna-token"],
        is_global=False,
        audience="COMERCIANTE",
        system_prompt=(
            "Eres el asistente interno de Sol y Luna para administradores. "
            "Ayudas con consultas sobre la tienda, configuracion, gestion de productos "
            "y soporte tecnico de Sol y Luna. "
            "Habla en espanol con un tono tecnico y directo."
        ),
        language="es",
    ),
}


def resolve_store(inbox_id: int) -> StoreConfig:
    if inbox_id in INBOX_MAP:
        return INBOX_MAP[inbox_id]
    return StoreConfig(
        store_name=f"tienda-{inbox_id}",
        channel_name="unknown",
        channel_tokens=[],
        is_global=False,
        audience="CLIENTE",
        system_prompt=(
            "Eres un asistente virtual. Ayuda al usuario con informacion disponible. "
            "Habla en espanol con un tono cercano y profesional."
        ),
        language="es",
    )
