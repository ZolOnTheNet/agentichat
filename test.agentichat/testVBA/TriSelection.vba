Sub TrierSelection()
    Dim ws As Worksheet
    Dim plage As Range
    Dim premiereLigne As Long
    
    ' Définir la feuille active
    Set ws = ActiveSheet
    
    ' Vérifier si une plage est sélectionnée
    If Selection.Cells.Count = 1 Then
        MsgBox "Veuillez sélectionner une plage de données à trier.", vbExclamation
        Exit Sub
    End If
    
    ' Définir la plage sélectionnée
    Set plage = Selection
    
    ' Obtenir la première ligne de la plage
    premiereLigne = plage.Row
    
    ' Trier la plage selon la première colonne (A)
    With ws.Sort
        .SortFields.Clear
        .SortFields.Add Key:=Range(plage.Cells(1, 1), plage.Cells(1, 1)), _
            SortOn:=xlSortOnValues, Order:=xlAscending, DataOption:=xlSortNormal
        .SetRange plage
        .Header = xlYes
        .MatchCase = False
        .Orientation = xlTopToBottom
        .Apply
    End With
    
    MsgBox "La zone sélectionnée a été triée avec succès !", vbInformation
End Sub