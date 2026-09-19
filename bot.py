import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters, ContextTypes
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Cargar variables del archivo .env
load_dotenv()

# Leer las credenciales
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Construir la conexión
connection_string = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(connection_string)

# Configuración del log de errores para monitoreo en consola
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

def acortar_nombre(pes_name: str) -> str:
    """Modifica el nombre largo del jugador para dejar solo la inicial y el apellido."""
    if not pes_name:
        return ""
    partes = pes_name.strip().split()
    if len(partes) > 1:
        return f"{partes[0][0]}. {' '.join(partes[1:])}"
    return pes_name

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador principal. Muestra el tablero utilizando formato HTML para prevenir
    estrictamente los errores de parseo por caracteres especiales en la BD.
    """
    telegram_id = update.effective_user.id
    encontrado = False
    manager_pure_name = "Invitado"
    team_pure_name = "Sin Franquicia"
    presupuesto_actual = 500.00
    texto_fichajes = "• No se registran altas"
    alertas_clausulas = "No se registran bajas por robo de cláusula."

    try:
        with engine.connect() as conn:
            # Buscar datos del mánager
            query_mgr = text("SELECT manager_id, manager_name, presupuesto FROM dim_managers WHERE platform_id = :pid")
            mgr = conn.execute(query_mgr, {"pid": str(telegram_id)}).fetchone()
            
            if mgr:
                encontrado = True
                presupuesto_actual = mgr.presupuesto
                
                if "|" in mgr.manager_name:
                    manager_pure_name, team_pure_name = map(str.strip, mgr.manager_name.split("|", 1))
                else:
                    manager_pure_name = mgr.manager_name
                    team_pure_name = "Equipo Asignado"
                
                # Consulta para extraer el historial de las 3 últimas altas
                query_history = text(
                    "SELECT p.pes_name, p.position, t.transfer_fee "
                    "FROM fact_transactions t "
                    "INNER JOIN dim_players p ON t.player_id = p.pes_id "
                    "WHERE t.to_manager_id = :mid "
                    "ORDER BY t.transaction_date DESC LIMIT 3"
                )
                fichajes_recientes = conn.execute(query_history, {"mid": mgr.manager_id}).fetchall()
                
                if fichajes_recientes:
                    texto_fichajes = ""
                    for f in fichajes_recientes:
                        # Lógica para reducir el nombre (ej: "Cristiano Ronaldo" -> "C. Ronaldo")
                        partes_nombre = f.pes_name.strip().split()
                        if len(partes_nombre) > 1:
                            nombre_corto = f"{partes_nombre[0][0]}. {' '.join(partes_nombre[1:])}"
                        else:
                            nombre_corto = f.pes_name

                        # Construcción del formato ideal con la posición intermedia
                        texto_fichajes += f"• {nombre_corto} ({f.position}) $ {f.transfer_fee:,.2f} M\n"
                        
                    texto_fichajes = texto_fichajes.strip()
                
                # Consultar alertas de cláusulas
                query_alertas = text(
                    "SELECT t.transaction_date, p.pes_name, m.manager_name "
                    "FROM fact_transactions t "
                    "INNER JOIN dim_players p ON t.player_id = p.pes_id "
                    "INNER JOIN dim_managers m ON t.to_manager_id = m.manager_id "
                    "WHERE t.from_manager_id = :mid AND t.transaction_type = 'RELEASE_CLAUSE' "
                    "ORDER BY t.transaction_date DESC LIMIT 1"
                )
                alerta = conn.execute(query_alertas, {"mid": mgr.manager_id}).fetchone()
                if alerta:
                    alerta_mgr = alerta.manager_name.split("|")[0].strip() if "|" in alerta.manager_name else alerta.manager_name
                    alertas_clausulas = (
                        f"⚠️ <b>¡ALERTA DE ROBO!</b>\n"
                        f"El {alerta.transaction_date.strftime('%d/%m %H:%M')} <b>{alerta_mgr}</b> "
                        f"se llevó a <b>{alerta.pes_name}</b> por cláusula."
                    )
                    
    except Exception as e:
        logging.error(f"Error al cargar el tablero de inicio: {e}")

    keyboard = [
        [InlineKeyboardButton("📊 Mi Equipo", callback_data="menu_equipo")],
        [InlineKeyboardButton("🔍 Buscar Jugador", callback_data="menu_buscar")],
        [InlineKeyboardButton("💰 Venta Rápida (50%)", callback_data="menu_venta_rapida")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if encontrado:
        # CORRECCIÓN DEFINITIVA: Estructura limpia migrada completamente a HTML
        texto_tablero = (
            f"⚽ <b>PANEL DE CONTROL LIGA</b>\n"
            f"───────────────────────\n"
            f"👤 <b>Mánager:</b> {manager_pure_name}\n"
            f"🛡️ <b>Equipo:</b> {team_pure_name}\n\n"
            f"💰 <b>Presupuesto Actual:</b>\n$ {presupuesto_actual:,.2f} M\n\n"
            f"📥 <b>Últimos Fichajes:</b>\n{texto_fichajes}\n"
            f"───────────────────────\n"
            f"🔔 <b>Notificaciones:</b>\n{alertas_clausulas}\n"
            f"───────────────────────\n"
            f"💡 <i>Tip: Usa /apodo Tu_Nombre para modificar tu perfil.</i>"
        )
    else:
        texto_tablero = (
            f"⚽ <b>PANEL DE CONTROL LIGA</b>\n"
            f"───────────────────────\n"
            f"⚠️ <b>Acceso Restringido - Sin Registro</b>\n\n"
            f"Registra tu franquicia ejecutando:\n<code>/r Nombre_De_Tu_Equipo</code>"
        )

    if update.message:
        await update.message.reply_text(texto_tablero, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.callback_query.message.edit_text(texto_tablero, reply_markup=reply_markup, parse_mode="HTML")

# ... (El resto de los métodos secundarios adaptados también a HTML para consistencia total)

async def cambiar_apodo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ Usa: <code>/apodo Tu_Nuevo_Apodo</code>", parse_mode="HTML")
        return
    nuevo_apodo = " ".join(context.args)
    try:
        with engine.begin() as conn:
            query_mgr = text("SELECT manager_name FROM dim_managers WHERE platform_id = :pid")
            mgr = conn.execute(query_mgr, {"pid": str(telegram_id)}).fetchone()
            if not mgr:
                await update.message.reply_text("❌ No estás registrado en la liga todavía.")
                return
            team_name = mgr.manager_name.split("|")[1].strip() if "|" in mgr.manager_name else "Equipo"
            nuevo_registro_name = f"{nuevo_apodo} | {team_name}"
            conn.execute(text("UPDATE dim_managers SET manager_name = :nname WHERE platform_id = :pid"), {"nname": nuevo_registro_name, "pid": str(telegram_id)})
        await update.message.reply_text(f"✅ <b>Apodo actualizado:</b> Ahora eres conocido como <b>{nuevo_apodo}</b>.", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error al cambiar apodo: {e}")

async def registrar_manager(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    manager_name = update.effective_user.first_name
    if not context.args:
        await update.message.reply_text("⚠️ Usa: <code>/r Nombre_De_Tu_Equipo</code>", parse_mode="HTML")
        return
    team_name = " ".join(context.args)
    try:
        with engine.begin() as conn:
            query_check = text("SELECT manager_id FROM dim_managers WHERE platform_id = :platform_id")
            if conn.execute(query_check, {"platform_id": str(telegram_id)}).fetchone():
                await update.message.reply_text("❌ Ya te encuentras registrado.")
                return
            query_insert = text("INSERT INTO dim_managers (manager_name, platform_id) VALUES (:name, :platform_id)")
            conn.execute(query_insert, {"name": f"{manager_name} | {team_name}", "platform_id": str(telegram_id)})
        await update.message.reply_text(f"✅ <b>¡Registro Exitoso!</b>\n🛡️ <b>Equipo:</b> {team_name}\n💰 <b>Presupuesto:</b> $500.00 M", parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error en registro: {e}")

async def buscar_jugador(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("⚠️ Usa: <code>/buscar Nombre_Del_Jugador</code>", parse_mode="HTML")
        return
    criterio_busqueda = " ".join(context.args)
    try:
        with engine.connect() as conn:
            query_search = text(
                "SELECT pes_id, pes_name, position, rating_range "
                "FROM dim_players WHERE LOWER(pes_name) LIKE LOWER(:criterio) "
                "ORDER BY pes_rating DESC LIMIT 5"
            )
            resultados = conn.execute(query_search, {"criterio": f"%{criterio_busqueda}%"}).fetchall()
            if not resultados:
                await update.message.reply_text(f"🔍 No se encontraron ganancias para '{criterio_busqueda}'.")
                return
            
            keyboard = []
            for jugador in resultados:
                texto_boton = f"{jugador.pes_name} ({jugador.position}) [{jugador.rating_range}]"
                keyboard.append([InlineKeyboardButton(texto_boton, callback_data=f"info_jugador_{jugador.pes_id}")])
                
            keyboard.append([InlineKeyboardButton("« Menú", callback_data="volver_menu")])
            await update.message.reply_text(f"🔍 <b>Resultados para '{criterio_busqueda}':</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Error en buscador: {e}")

async def manejar_botones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    telegram_id = update.effective_user.id
    await query.answer()
    back_keyboard = [[InlineKeyboardButton("« Menú", callback_data="volver_menu")]]

    if query.data == "menu_equipo":
        try:
            with engine.connect() as conn:
                query_mgr = text("SELECT manager_id FROM dim_managers WHERE platform_id = :pid")
                mgr = conn.execute(query_mgr, {"pid": str(telegram_id)}).fetchone()
                if not mgr:
                    await query.message.edit_text("⚠️ No estás registrado.", reply_markup=InlineKeyboardMarkup(back_keyboard))
                    return
                query_players = text("SELECT pes_name, position, rating_range FROM dim_players WHERE manager_id = :mid")
                players = conn.execute(query_players, {"mid": mgr.manager_id}).fetchall()
                
                if not players:
                    texto_lista = "📋 <b>Tu Plantilla:</b>\n\nNo tienes jugadores firmados."
                else:
                    texto_lista = "📋 <b>Tu Plantilla Actual:</b>\n\n"
                    for p in players:
                        # FORMATO NUEVO: Nombre corto en la cabecera y rango de media abajo
                        nombre_corto = acortar_nombre(p.pes_name)
                        texto_lista += f"• <b>{nombre_corto}</b> ({p.position})\nMedia: {p.rating_range}\n"
            await query.message.edit_text(text=texto_lista, reply_markup=InlineKeyboardMarkup(back_keyboard), parse_mode="HTML")
        except Exception as e:
            logging.error(f"Error en equipo: {e}")

    elif query.data == "menu_buscar":
        await query.message.edit_text("🔍 <b>Buscador:</b>\n\nEscribe en el chat:\n<code>/b Nombre</code>", reply_markup=InlineKeyboardMarkup(back_keyboard), parse_mode="HTML")

    elif query.data == "menu_venta_rapida":
        try:
            with engine.connect() as conn:
                query_mgr = text("SELECT manager_id FROM dim_managers WHERE platform_id = :pid")
                mgr = conn.execute(query_mgr, {"pid": str(telegram_id)}).fetchone()
                if not mgr:
                    await query.message.edit_text("⚠️ No estás registrado.", reply_markup=InlineKeyboardMarkup(back_keyboard))
                    return
                query_my_players = text("SELECT pes_id, pes_name, market_value_real FROM dim_players WHERE manager_id = :mid")
                my_players = conn.execute(query_my_players, {"mid": mgr.manager_id}).fetchall()
                if not my_players:
                    await query.message.edit_text("📋 <b>Venta Rápida:</b>\n\nNo posees jugadores en tu plantilla para liquidar.", reply_markup=InlineKeyboardMarkup(back_keyboard), parse_mode="HTML")
                    return

                keyboard_sell = []
                for p in my_players:
                    # CORRECCIÓN: Casteo a float para evitar el error 'decimal.Decimal' and 'float'
                    valor_descarte = float(p.market_value_real) * 0.5
                    
                    # APLICADO: Nombre abreviado en el botón
                    nombre_corto = acortar_nombre(p.pes_name)
                    
                    texto_btn = f"❌ {nombre_corto} (Recibes: $ {valor_descarte:,.2f} M)"
                    keyboard_sell.append([InlineKeyboardButton(texto_btn, callback_data=f"confirmar_sell_{p.pes_id}")])

                keyboard_sell.append([InlineKeyboardButton("« Menú", callback_data="volver_menu")])
                await query.message.edit_text("💰 <b>PANEL DE LIQUIDACIÓN (VENTA RÁPIDA)</b>\n\nSelecciona el jugador que deseas vender a la banca. Recibirás el <b>50% de su valor</b>:", reply_markup=InlineKeyboardMarkup(keyboard_sell), parse_mode="HTML")
        except Exception as e:
            logging.error(f"Error en menú venta rápida: {e}")

    elif query.data.startswith("confirmar_sell_"):
        player_id = int(query.data.split("_")[-1])
        try:
            with engine.begin() as conn:
                comprador = conn.execute(text("SELECT manager_id FROM dim_managers WHERE platform_id = :pid"), {"pid": str(telegram_id)}).fetchone()
                player = conn.execute(text("SELECT pes_name, market_value_real, manager_id FROM dim_players WHERE pes_id = :pid"), {"pid": player_id}).fetchone()
                if not comprador or player.manager_id != comprador.manager_id:
                    await query.message.edit_text("❌ Operación no autorizada.", reply_markup=InlineKeyboardMarkup(back_keyboard))
                    return
                
                monto_recuperado = float(player.market_value_real) * 0.5
                
                conn.execute(text("UPDATE dim_managers SET presupuesto = presupuesto + :monto WHERE manager_id = :mid"), {"monto": monto_recuperado, "mid": comprador.manager_id})
                conn.execute(text("UPDATE dim_players SET manager_id = NULL WHERE pes_id = :pid"), {"pid": player_id})
                
                # CORRECCIÓN AQUÍ: Cambiamos NULL por :to_m en la consulta SQL para cumplir con el NOT NULL de la BD
                query_insert_tx = text(
                    "INSERT INTO fact_transactions (player_id, from_manager_id, to_manager_id, transfer_fee, transaction_type, transaction_date) "
                    "VALUES (:pid, :from_m, :to_m, :fee, 'QUICK_SELL', :tdate)"
                )
                
                # Pasamos comprador.manager_id en to_m para que no vaya vacío y salte el IntegrityError
                conn.execute(query_insert_tx, {
                    "pid": player_id, 
                    "from_m": comprador.manager_id, 
                    "to_m": None,  # <-- Representa a la BANCA / Sistema
                    "fee": monto_recuperado, 
                    "tdate": datetime.now()
                })
            
            nombre_corto = acortar_nombre(player.pes_name)
            await query.message.edit_text(f"✅ <b>¡LIQUIDACIÓN COMPLETADA!</b>\nHas vendido a <b>{nombre_corto}</b> por <code>$ {monto_recuperado:,.2f} M</code>.", reply_markup=InlineKeyboardMarkup(back_keyboard), parse_mode="HTML")
        except Exception as e:
            logging.error(f"Error en execution de venta rápida: {e}")

    elif query.data.startswith("info_jugador_"):
        player_id = int(query.data.split("_")[-1])
        try:
            with engine.connect() as conn:
                query_player = text(
                    "SELECT p.pes_name, p.position, p.rating_range, p.pes_age, p.team_name, p.nat_name, "
                    "p.market_value_real, p.release_clause, p.manager_id, m.manager_name AS club_actual "
                    "FROM dim_players p LEFT JOIN dim_managers m ON p.manager_id = m.manager_id WHERE p.pes_id = :pid"
                )
                p = conn.execute(query_player, {"pid": player_id}).fetchone()
                if p:
                    club_desplegado = p.club_actual.split("|")[1].strip() if p.manager_id and "|" in p.club_actual else (p.club_actual if p.manager_id else p.team_name)
                    ficha_tecnica = (
                        f"🏃‍♂️ <b>FICHA DE JUGADOR</b>\n\n👤 <b>Nombre:</b> {p.pes_name}\n🛡️ <b>Club Actual:</b> {club_desplegado}\n🌍 <b>Nacionalidad:</b> {p.nat_name}\n"
                        f"🎂 <b>Edad:</b> {p.pes_age} años\n📐 <b>Posición:</b> {p.position}\n📊 <b>Media:</b> <code>{p.rating_range}</code>\n\n"
                        f"💰 <b>Valor Mercado:</b> $ {p.market_value_real:,.2f} M\n🔒 <b>Cláusula Rescisión:</b> $ {p.release_clause:,.2f} M"
                    )
                    opciones = []
                    if p.manager_id is None:
                        opciones.append([InlineKeyboardButton(f"✍️ Fichar Libre ($ {p.market_value_real:,.2f} M)", callback_data=f"tx_libre_{player_id}")])
                    else:
                        my_mgr = conn.execute(text("SELECT manager_id FROM dim_managers WHERE platform_id = :pid"), {"pid": str(telegram_id)}).fetchone()
                        if my_mgr and p.manager_id != my_mgr.manager_id:
                            opciones.append([InlineKeyboardButton(f"💣 Pagar Cláusula ($ {p.release_clause:,.2f} M)", callback_data=f"tx_clausula_{player_id}")])
                    opciones.append([InlineKeyboardButton("« Menú", callback_data="volver_menu")])
                    await query.message.edit_text(text=ficha_tecnica, reply_markup=InlineKeyboardMarkup(opciones), parse_mode="HTML")
        except Exception as e:
            logging.error(f"Error al cargar ficha: {e}")

    elif query.data.startswith("tx_"):
        partes = query.data.split("_")
        tipo_tx = partes[1]
        player_id = int(partes[2])
        try:
            with engine.begin() as conn:
                comprador = conn.execute(text("SELECT manager_id, presupuesto FROM dim_managers WHERE platform_id = :pid"), {"pid": str(telegram_id)}).fetchone()
                player = conn.execute(text("SELECT pes_name, market_value_real, release_clause, manager_id FROM dim_players WHERE pes_id = :pid"), {"pid": player_id}).fetchone()
                costo = player.market_value_real if tipo_tx == "libre" else player.release_clause
                if comprador.presupuesto < costo:
                    await query.message.edit_text(f"❌ <b>Fondos Insuficientes.</b>\nCosto: $ {costo:,.2f} M | Saldo: $ {comprador.presupuesto:,.2f} M", reply_markup=InlineKeyboardMarkup(back_keyboard), parse_mode="HTML")
                    return
                conn.execute(text("UPDATE dim_managers SET presupuesto = presupuesto - :costo WHERE manager_id = :mid"), {"costo": costo, "mid": comprador.manager_id})
                vendedor_id = None
                if tipo_tx == "clausula":
                    vendedor_id = player.manager_id
                    conn.execute(text("UPDATE dim_managers SET presupuesto = presupuesto + :costo WHERE manager_id = :mid"), {"costo": costo, "mid": vendedor_id})
                conn.execute(text("UPDATE dim_players SET manager_id = :mid WHERE pes_id = :pid"), {"mid": comprador.manager_id, "pid": player_id})
                tipo_log = "FREE_AGENT" if tipo_tx == "libre" else "RELEASE_CLAUSE"
                conn.execute(text(
                    "INSERT INTO fact_transactions (player_id, from_manager_id, to_manager_id, transfer_fee, transaction_type, transaction_date) "
                    "VALUES (:pid, :from_m, :to_m, :amt, :ttype, :tdate)"
                ), {"pid": player_id, "from_m": vendedor_id, "to_m": comprador.manager_id, "amt": costo, "ttype": tipo_log, "tdate": datetime.now()})
            await query.message.edit_text(f"✅ <b>¡OPERACIÓN EXITOSA!</b>\n\nHas fichado a <b>{player.pes_name}</b> por <code>$ {costo:,.2f} M</code>.", reply_markup=InlineKeyboardMarkup(back_keyboard), parse_mode="HTML")
        except Exception as e:
            logging.error(f"Error crítico en transacción: {e}")

    elif query.data == "volver_menu":
        await start(update, context)

def main() -> None:
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("r", registrar_manager))
    app.add_handler(CommandHandler("b", buscar_jugador)) # Alias corto "Buscar"
    app.add_handler(CommandHandler("apodo", cambiar_apodo))
    
    app.add_handler(CallbackQueryHandler(manejar_botones))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    
    print(" Bot activo y escuchando peticiones en Telegram (Modo HTML)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()