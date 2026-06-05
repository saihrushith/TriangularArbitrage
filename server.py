import asyncio
import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import main_bot

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Config(BaseModel):
    api_key: str
    secret_key: str
    starting_amount: float
    min_profit_threshold: float

@app.get("/api/status")
async def get_status():
    config_copy = main_bot.BOT_STATE["config"].copy()
    
    # Mask API Keys so they are not exposed to the frontend
    api_key = config_copy.get("api_key", "")
    if len(api_key) > 8:
        config_copy["api_key"] = api_key[:4] + "..." + api_key[-4:]
    elif api_key:
        config_copy["api_key"] = "****"
        
    secret_key = config_copy.get("secret_key", "")
    if secret_key:
        config_copy["secret_key"] = "****************"

    return {
        "is_running": main_bot.BOT_STATE["is_running"],
        "config": config_copy,
        "stats": main_bot.BOT_STATE["stats"]
    }

@app.post("/api/config")
async def update_config(config: Config):
    new_config = config.dict()
    current_config = main_bot.BOT_STATE["config"]
    
    # Only update keys if they are not the masked placeholder
    if "..." not in new_config["api_key"] and "****" not in new_config["api_key"]:
        current_config["api_key"] = new_config["api_key"]
    
    if "********" not in new_config["secret_key"]:
        current_config["secret_key"] = new_config["secret_key"]
        
    current_config["starting_amount"] = new_config["starting_amount"]
    current_config["min_profit_threshold"] = new_config["min_profit_threshold"]
    
    return {"status": "success"}

@app.post("/api/start")
async def start_bot():
    if not main_bot.BOT_STATE["is_running"]:
        if not main_bot.BOT_STATE["config"]["api_key"]:
            return {"status": "error", "message": "API Key is required"}
        main_bot.BOT_STATE["is_running"] = True
        asyncio.create_task(main_bot.run_bot_loop())
        return {"status": "success", "message": "Bot started"}
    return {"status": "error", "message": "Bot is already running"}

@app.post("/api/stop")
async def stop_bot():
    if main_bot.BOT_STATE["is_running"]:
        main_bot.BOT_STATE["is_running"] = False
        return {"status": "success", "message": "Bot stopping..."}
    return {"status": "error", "message": "Bot is not running"}

@app.get("/api/trades")
async def get_trades():
    return {"trades": main_bot.BOT_STATE["trades_history"]}

@app.get("/api/ping")
async def ping():
    return {"status": "alive"}

if __name__ == "__main__":
    import uvicorn
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
