import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import io
import aiohttp
import random

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

    @commands.command()
    async def caption(self, ctx, *, text):
        """Add meme-style caption to an image"""
        if not ctx.message.reference:
            await ctx.send("Please reply to an image to add a caption!")
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
                        image = Image.open(io.BytesIO(image_data))
                        
                        # Convert to RGB if necessary
                        if image.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', image.size, (255, 255, 255))
                            background.paste(image, mask=image.split()[-1])
                            image = background
                        
                        # Make a white bar at the top for the caption
                        bar_height = min(200, image.width // 3)  # Reasonable height, not too tall
                        new_height = image.height + bar_height
                        new_image = Image.new('RGB', (image.width, new_height), (255, 255, 255))
                        new_image.paste(image, (0, bar_height))
                        
                        # Create a blank image for the text at much higher resolution (for larger text)
                        text_img = Image.new('RGB', (image.width * 5, bar_height * 5), (255, 255, 255))
                        draw = ImageDraw.Draw(text_img)
                        
                        # Use default font
                        font = ImageFont.load_default()
                        
                        # Draw text in big size
                        draw.text((text_img.width // 10, text_img.height // 3), text.upper(), font=font, fill=(0, 0, 0))
                        
                        # Resize down to fit the bar (this makes the font look bigger)
                        text_img = text_img.resize((image.width, bar_height), Image.Resampling.LANCZOS)
                        
                        # Paste text image onto the white bar
                        new_image.paste(text_img, (0, 0))
                        
                        # Save and send
                        output = io.BytesIO()
                        new_image.save(output, format='PNG')
                        output.seek(0)
                        
                        await ctx.send(file=discord.File(output, filename='meme.png'))
                    else:
                        await ctx.send("Failed to download the image!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command()
    async def fry(self, ctx):
        """Deepfry an image"""
        if not ctx.message.reference:
            await ctx.send("Please reply to an image to deepfry it!")
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
                        image = Image.open(io.BytesIO(image_data))
                        
                        # Convert to RGB if necessary
                        if image.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', image.size, (255, 255, 255))
                            background.paste(image, mask=image.split()[-1])
                            image = background
                        
                        # Apply deepfry effects
                        # Increase contrast
                        contrast = ImageEnhance.Contrast(image)
                        image = contrast.enhance(2.0)
                        
                        # Increase saturation
                        saturation = ImageEnhance.Color(image)
                        image = saturation.enhance(2.0)
                        
                        # Increase sharpness
                        sharpness = ImageEnhance.Sharpness(image)
                        image = sharpness.enhance(2.0)
                        
                        # Add noise
                        pixels = image.load()
                        for i in range(image.size[0]):
                            for j in range(image.size[1]):
                                if random.random() < 0.1:  # 10% chance for noise
                                    noise = random.randint(-30, 30)
                                    r, g, b = pixels[i, j]
                                    pixels[i, j] = (
                                        max(0, min(255, r + noise)),
                                        max(0, min(255, g + noise)),
                                        max(0, min(255, b + noise))
                                    )
                        
                        # Save and send
                        output = io.BytesIO()
                        image.save(output, format='PNG')
                        output.seek(0)
                        
                        await ctx.send(file=discord.File(output, filename='deepfried.png'))
                    else:
                        await ctx.send("Failed to download the image!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command()
    async def mirror(self, ctx):
        """Mirror an image horizontally"""
        if not ctx.message.reference:
            await ctx.send("Please reply to an image to mirror it!")
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
                        image = Image.open(io.BytesIO(image_data))
                        
                        # Convert to RGB if necessary
                        if image.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', image.size, (255, 255, 255))
                            background.paste(image, mask=image.split()[-1])
                            image = background
                        
                        # Mirror the image
                        mirrored_image = image.transpose(Image.FLIP_LEFT_RIGHT)
                        
                        # Save and send
                        output = io.BytesIO()
                        mirrored_image.save(output, format='PNG')
                        output.seek(0)
                        
                        await ctx.send(file=discord.File(output, filename='mirrored.png'))
                    else:
                        await ctx.send("Failed to download the image!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(ImageCog(bot)) 