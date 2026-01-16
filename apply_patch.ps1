 = 'C:\Users\anton\EOMTemplateTools\EOMTemplateTools.extension\EOM.tab\04_Sockets.panel\Sockets.pulldown\04_AC.pushbutton\script.py'

if (-not (Test-Path )) {
    Write-Host 'File not found: '
    exit 1
}

 = Get-Content -Path  -Raw -Encoding UTF8

# Part 1: Insert facade_dir_vec calculation
 = '        if not c_ext:
            continue'
 = '        if not c_ext:
            continue

        facade_dir_vec = None
        try:
            fd = c_ext.GetEndPoint(1) - c_ext.GetEndPoint(0)
            if fd.GetLength() > 1e-9:
                facade_dir_vec = fd.Normalize()
        except Exception:
            facade_dir_vec = None'

# Normalize line endings to LF for comparison if needed, or just be careful.
# Python file likely uses CRLF on Windows.
 =  -replace '
','
' -replace '
', 

 =  -replace '
','
' -replace '
',


if ( -match 'facade_dir_vec = None') {
    Write-Host 'Part 1 already applied or similar code found.'
} elseif (.Contains()) {
     = .Replace(, )
    Write-Host 'Applied Part 1.'
} else {
    Write-Host 'Target 1 not found.'
}

# Part 2: Insert parallel check
 = '                try:
                    wall_side = link_doc.GetElement(s_adj.ElementId)
                except Exception:
                    wall_side = None'
 = '                try:
                    wall_side = link_doc.GetElement(s_adj.ElementId)
                except Exception:
                    wall_side = None

                if facade_dir_vec:
                    try:
                        ad = c_adj.GetEndPoint(1) - c_adj.GetEndPoint(0)
                        if ad.GetLength() > 1e-9:
                            ad = ad.Normalize()
                            if abs(float(facade_dir_vec.DotProduct(ad))) > 0.5:
                                continue
                    except Exception:
                        pass'
                        
 =  -replace '
','
' -replace '
',

 =  -replace '
','
' -replace '
',


if ( -match 'if abs\(float\(facade_dir_vec.DotProduct\(ad\)\)\) > 0.5') {
    Write-Host 'Part 2 already applied.'
} elseif (.Contains()) {
     = .Replace(, )
    Write-Host 'Applied Part 2.'
} else {
    Write-Host 'Target 2 not found.'
}

# Part 3: Remove old perpendicularity check
 = '(?ms)                if wall_side and isinstance\(wall_side, DB\.Wall\):.*?(?=                    wall_any = wall_side)'
 = '                if wall_side and isinstance(wall_side, DB.Wall):' + 


if ( -match 'is_perp = _is_wall_perpendicular_to_basket') {
    = [regex]::Replace(, , )
   Write-Host 'Applied Part 3.'
} else {
   Write-Host 'Part 3 already applied (or not found).'
}

Set-Content -Path  -Value  -Encoding UTF8 -NoNewline
Write-Host 'Done.'
