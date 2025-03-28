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
        await ctx.send("This command is currently broken, sorry :((")

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

    #### SLASH COMMANDS ####

    @commands.slash_command(name="gif", description="Convert an image to GIF format")
    async def slash_gif(self, interaction: discord.Interaction):
        """Convert an image to GIF format"""
        if not interaction.message.reference:
            await interaction.response.send_message("Please reply to an image to convert it to a GIF!", ephemeral=True)
            return
        
        try:
            referenced_message = await interaction.channel.fetch_message(interaction.message.reference.message_id)
            if not referenced_message.attachments:
                await interaction.response.send_message("The referenced message doesn't contain any images!", ephemeral=True)
                return
            
            attachment = referenced_message.attachments[0]
            if not attachment.content_type.startswith('image'):
                await interaction.response.send_message("The referenced message doesn't contain a valid image!", ephemeral=True)
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
                        await interaction.response.send_message(file=discord.File(output, filename='converted.gif'))
                    else:
                        await interaction.response.send_message("Failed to download the image!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.slash_command(name="caption", description="Add meme-style caption to an image")
    async def slash_caption(self, interaction: discord.Interaction, text: str):
        """Add meme-style caption to an image"""
        await interaction.response.send_message("This command is currently broken, sorry :((")

    @commands.slash_command(name="fry", description="Deepfry an image")
    async def slash_fry(self, interaction: discord.Interaction):
        """Deepfry an image"""
        if not interaction.message.reference:
            await interaction.response.send_message("Please reply to an image to deepfry it!", ephemeral=True)
            return
        
        try:
            referenced_message = await interaction.channel.fetch_message(interaction.message.reference.message_id)
            if not referenced_message.attachments:
                await interaction.response.send_message("The referenced message doesn't contain any images!", ephemeral=True)
                return
            
            attachment = referenced_message.attachments[0]
            if not attachment.content_type.startswith('image'):
                await interaction.response.send_message("The referenced message doesn't contain a valid image!", ephemeral=True)
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
                        
                        await interaction.response.send_message(file=discord.File(output, filename='deepfried.png'))
                    else:
                        await interaction.response.send_message("Failed to download the image!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

    @commands.slash_command(name="mirror", description="Mirror an image horizontally")
    async def slash_mirror(self, interaction: discord.Interaction):
        """Mirror an image horizontally"""
        if not interaction.message.reference:
            await interaction.response.send_message("Please reply to an image to mirror it!", ephemeral=True)
            return
        
        try:
            referenced_message = await interaction.channel.fetch_message(interaction.message.reference.message_id)
            if not referenced_message.attachments:
                await interaction.response.send_message("The referenced message doesn't contain any images!", ephemeral=True)
                return
            
            attachment = referenced_message.attachments[0]
            if not attachment.content_type.startswith('image'):
                await interaction.response.send_message("The referenced message doesn't contain a valid image!", ephemeral=True)
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
                        
                        await interaction.response.send_message(file=discord.File(output, filename='mirrored.png'))
                    else:
                        await interaction.response.send_message("Failed to download the image!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ImageCog(bot)) 