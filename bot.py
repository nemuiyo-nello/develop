import discord
from discord.ext import commands
import asyncio
import asyncpg
import os

# ボットの初期化
intents = discord.Intents.default()
intents.message_content = True  # メッセージコンテンツのインテントを有効にする
bot = commands.Bot(command_prefix="!", intents=intents)


# データベースに接続する関数
async def init_db():
    """データベース接続プールを初期化"""
    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("環境変数 'DATABASE_URL' が設定されていません。")
            return None
        return await asyncpg.create_pool(dsn=db_url)
    except Exception as e:
        print(f"データベース接続エラー: {e}")
        return None


# テーブルを作成する関数
async def create_tables():
    """データベースに必要なテーブルを作成する"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("環境変数 'DATABASE_URL' が設定されていません。")
        return

    try:
        # データベースに接続
        conn = await asyncpg.connect(dsn=db_url)
        print("データベースに接続しました。")

        # テーブル作成SQL
        create_table_query = """
        CREATE TABLE IF NOT EXISTS server_config (
            guild_id BIGINT PRIMARY KEY,               -- サーバーのID (主キー)
            button_channel_id BIGINT,                 -- ボタン設置用のチャンネルID
            notify_channel_id BIGINT,                 -- 通知用のチャンネルID
            sub_channel_id BIGINT,                    -- サブ通知用のチャンネルID
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- レコード作成日時
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- レコード更新日時
        );
        """
        # クエリを実行
        await conn.execute(create_table_query)
        print("テーブルを作成しました。")

    except Exception as e:
        print(f"テーブル作成中にエラーが発生しました: {e}")
    finally:
        await conn.close()
        print("データベース接続を閉じました。")


# サーバーごとの設定を保存する関数（ボタンチャンネルID）
async def save_button_channel(pool, guild_id, button_channel_id):
    async with pool.acquire() as connection:
        await connection.execute(""" 
            INSERT INTO server_config (guild_id, button_channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE
            SET button_channel_id = $2
        """, guild_id, button_channel_id)


# サーバーごとの設定を読み込む関数
async def load_config(pool, guild_id):
    async with pool.acquire() as connection:
        return await connection.fetchrow("SELECT * FROM server_config WHERE guild_id = $1", guild_id)


# ボタンの作成
class MyView(discord.ui.View):
    def __init__(self, notify_channel_id):
        super().__init__(timeout=None)  # timeoutをNoneに設定して無効化
        self.notify_channel_id = notify_channel_id  # 通知チャンネルのIDを保存

    # 「🚀 ちゃむる！」ボタン
    @discord.ui.button(label="🚀 ちゃむる！", style=discord.ButtonStyle.success)
    async def chamuru_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = bot.get_channel(self.notify_channel_id)
        await interaction.response.send_message("メッセージをお知らせチャンネルに送信するよっ！", ephemeral=True)

        if channel is not None:
            user_nick = interaction.user.display_name  # サーバーニックネームまたは表示名を取得
            try:
                await channel.send(f"@everyone\n🌟 わーい！掘るちゃむよ～！🌟\n {user_nick} が教えてくれたよっ！🎉")
            except discord.Forbidden:
                await interaction.response.send_message("メッセージを送信する権限がありません。", ephemeral=True)
            except discord.HTTPException as e:
                print(f"メッセージ送信時のエラー: {e}")
        else:
            await interaction.response.send_message("指定したチャンネルが見つかりませんでした。", ephemeral=True)


# ボタンチャンネルIDの設定コマンド
@bot.command()
@commands.has_permissions(administrator=True)
async def sb(ctx):
    button_channel_id = ctx.channel.id  # コマンドが実行されたチャンネルのIDを取得
    await save_button_channel(bot.db_pool, ctx.guild.id, button_channel_id)
    await ctx.send(f"ボタンチャンネルを {ctx.channel.name} に設定しました！")


# ボットが起動したときの処理
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    bot.db_pool = await init_db()

    # テーブル作成を実行
    await create_tables()
    print("Bot is ready!")


# ボットを起動
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')  # 環境変数からボットのトークンを取得
    bot.run(token)
