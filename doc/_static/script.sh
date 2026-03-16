# The commit where the pictures have no text is cb90d099f25d778098aa6af8018f2aaa3947e82d

for img in *.jpg; do
  magick "$img" -gravity SouthWest -pointsize 40 -fill white -annotate +10+5 "AI Generated" "$img"
done
