from PIL import Image
im = Image.open("D:/PDF editor/assets/icons/pdf_editor.ico")
im = im.convert("RGBA")
im.save("D:/PDF editor/assets/icons/preview.png")
print("ok", im.size)
