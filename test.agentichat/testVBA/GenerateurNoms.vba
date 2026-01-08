' Générateur de noms aléatoires
' Fonction principale qui retourne un nom aléatoire à chaque appel

Dim nomsPrecedents() As String
Dim indexPrecedents As Integer

Function GenererNomAleatoire() As String
    Dim prenoms(1 To 20) As String
    Dim nomsFamille(1 To 20) As String
    Dim prenom As String
    Dim nomFamille As String
    Dim nomComplete As String
    Dim i As Integer
    Dim indexPrenom As Integer
    Dim indexNom As Integer
    
    ' Liste de prénoms
    prenoms(1) = "Jean"
    prenoms(2) = "Marie"
    prenoms(3) = "Pierre"
    prenoms(4) = "Sophie"
    prenoms(5) = "Luc"
    prenoms(6) = "Claire"
    prenoms(7) = "Paul"
    prenoms(8) = "Élise"
    prenoms(9) = "Michel"
    prenoms(10) = "Isabelle"
    prenoms(11) = "Thomas"
    prenoms(12) = "Catherine"
    prenoms(13) = "Nicolas"
    prenoms(14) = "Antoinette"
    prenoms(15) = "Julien"
    prenoms(16) = "Martine"
    prenoms(17) = "François"
    prenoms(18) = "Sylvie"
    prenoms(19) = "Hervé"
    prenoms(20) = "Dominique"
    
    ' Liste de noms de famille
    nomsFamille(1) = "Martin"
    nomsFamille(2) = "Dubois"
    nomsFamille(3) = "Durand"
    nomsFamille(4) = "Robert"
    nomsFamille(5) = "Richard"
    nomsFamille(6) = "Petit"
    nomsFamille(7) = "Roux"
    nomsFamille(8) = "Moreau"
    nomsFamille(9) = "Simon"
    nomsFamille(10) = "Laurent"
    nomsFamille(11) = "Leroy"
    nomsFamille(12) = "Bernard"
    nomsFamille(13) = "Fournier"
    nomsFamille(14) = "Girard"
    nomsFamille(15) = "Voisin"
    nomsFamille(16) = "Marchand"
    nomsFamille(17) = "Lefebvre"
    nomsFamille(18) = "Dupont"
    nomsFamille(19) = "Mercier"
    nomsFamille(20) = "Blanc"
    
    ' Sélection aléatoire
    Randomize
    indexPrenom = Int((20 * Rnd) + 1)
    indexNom = Int((20 * Rnd) + 1)
    
    ' Combinaison du prénom et du nom de famille
    prenom = prenoms(indexPrenom)
    nomFamille = nomsFamille(indexNom)
    nomComplete = prenom & " " & nomFamille
    
    GenererNomAleatoire = nomComplete
End Function

' Fonction pour obtenir plusieurs noms différents (sans doublon)
Function GenererNomsSansDoublon(nombre As Integer) As String
    Dim resultat As String
    Dim i As Integer
    Dim nom As String
    Dim nomsUtilises() As String
    Dim indexUtilises As Integer
    
    ReDim nomsUtilises(1 To nombre)
    indexUtilises = 0
    
    For i = 1 To nombre
        Do
            nom = GenererNomAleatoire()
            ' Vérifier si le nom est déjà utilisé
            Dim j As Integer
            Dim dejaUtilise As Boolean
            dejaUtilise = False
            
            For j = 1 To indexUtilises
                If nomsUtilises(j) = nom Then
                    dejaUtilise = True
                    Exit For
                End If
            Next j
            
            If Not dejaUtilise Then
                indexUtilises = indexUtilises + 1
                nomsUtilises(indexUtilises) = nom
                resultat = resultat & nom & vbCrLf
                Exit Do
            End If
        Loop
    Next i
    
    GenererNomsSansDoublon = Trim(resultat)
End Function

' Fonction pour réinitialiser les noms précédents (si utilisation de la version sans doublon)
Sub ReinitialiserNoms()
    Erase nomsPrecedents
    indexPrecedents = 0
End Sub