 # Create simple PNG icons for pyRevit buttons
 Add-Type -AssemblyName System.Drawing
 
 function Create-Icon {
     param(
         [string]$Path,
         [int]$R,
         [int]$G,
         [int]$B,
         [string]$Text = ""
     )
     
     $size = 32
     $bmp = New-Object System.Drawing.Bitmap($size, $size)
     $g = [System.Drawing.Graphics]::FromImage($bmp)
     $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
     
     # Background
     $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, $R, $G, $B))
     $g.FillRectangle($brush, 0, 0, $size, $size)
     
     # Text if provided
     if ($Text) {
         $font = New-Object System.Drawing.Font("Arial", 10, [System.Drawing.FontStyle]::Bold)
         $textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
         $format = New-Object System.Drawing.StringFormat
         $format.Alignment = [System.Drawing.StringAlignment]::Center
         $format.LineAlignment = [System.Drawing.StringAlignment]::Center
         $rect = New-Object System.Drawing.RectangleF(0, 0, $size, $size)
         $g.DrawString($Text, $font, $textBrush, $rect, $format)
     }
     
     $g.Dispose()
     $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
     $bmp.Dispose()
     Write-Host "Created: $Path"
 }
 
 $base = "C:\Users\anton\EOMTemplateTools\EOMTemplateTools.extension\EOM.tab"
 
 # Lighting panel
 Create-Icon "$base\02_Lighting.panel\Place_Lights_EntranceDoors.pushbutton\icon.png" 74 144 226 "D"
 Create-Icon "$base\02_Lighting.panel\Place_Lights_LiftShaft.pushbutton\icon.png" 96 125 139 "L"
 Create-Icon "$base\02_Lighting.panel\Place_Lights_PK.pushbutton\icon.png" 229 57 53 "PK"
 Create-Icon "$base\02_Lighting.panel\99_ListLinkRoomNames.pushbutton\icon.png" 156 39 176 "R"
 
 # Maintenance panel
 Create-Icon "$base\99_Maintenance.panel\Delete_All_AutoEOM.pushbutton\icon.png" 211 47 47 "X"
 Create-Icon "$base\99_Maintenance.panel\Undo_Placement.pushbutton\icon.png" 255 152 0 "U"
 
 Write-Host "All icons created!"
