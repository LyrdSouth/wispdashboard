import discord
from discord.ext import commands
from PIL import Image
import io
import aiohttp

class ImageCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.EMBED_COLOR = discord.Color.from_rgb(187, 144, 252)  # Soft purple color

    @commands.command()
    async def gif(self, ctx):
        """Convert an image to GIF format"""
        if not ctx.message.reference:
            await ctx.send("Please reply to an image to convert it to a GIF!")
            return
        
        try:
            referenced_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if not referenced_message.attachments:
                await ctx.send("The referenced message doesn't contain any images!")
                return
            
            attachment = referenced_message.attachments[0]
            if not attachment.content_type.startswith('image'):
                await ctx.send("The referenced message doesn't contain a valid image!")
                return
            
            # Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        
                        # Convert to GIF
                        image = Image.open(io.BytesIO(image_data))
                        if image.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', image.size, (255, 255, 255))
                            background.paste(image, mask=image.split()[-1])
                            image = background
                        
                        # Save as GIF
                        output = io.BytesIO()
                        image.save(output, format='GIF')
                        output.seek(0)
                        
                        # Send the GIF
                        await ctx.send(file=discord.File(output, filename='converted.gif'))
                    else:
                        await ctx.send("Failed to download the image!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(ImageCog(bot)) 