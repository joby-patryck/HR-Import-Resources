import pandas

# Get filename through stdin
filenname = input().strip('"')

while (filenname != 'q'):
    data = pandas.read_csv(filenname)
    # Job Assignments file
    if "job assignments" in filenname.lower():
        data = data[~(data["useridnumber"].isna() | (data["useridnumber"] == ""))]
        data["Manager email"] = data["Manager email"].fillna("#N/A")
        for name_index in data.index:
            data.loc[name_index, "Manager email"] = data["Manager email"][name_index].lower()
        for name_index in data.index:
            data.loc[name_index, "useridnumber"] = data["useridnumber"][name_index].lower()
    # Users file
    else:
        data = data[~(data["idnumber"].isna() | (data["idnumber"] == ""))]
        for name_index in data.index:
            data.loc[name_index, "idnumber"] = data["idnumber"][name_index].lower()

    data.to_csv(filenname)

    print("Success!")

    filenname = input().strip('"')