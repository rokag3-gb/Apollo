namespace Apollo.Core.Model;

public class StoredProcedureList
{
    public List<StoredProcedureModel> Procedures { get; set; } = new();
}

public class StoredProcedureModel
{
    public required string Name { get; set; }
    public string? Caller { get; set; } // 호출자: User, Admin, Batch (sp_catalog 테이블에서 가져옴)
    public List<ParameterMetadata>? Parameters { get; set; } = new();
}

public class ParameterMetadata
{
    public required string Name { get; set; }        // E.g., @UserID
    public required string SqlTypeName { get; set; } // E.g., int, varchar, datetime
    public int MaxLength { get; set; }               // 최대길이 (varchar, nvarchar, char, nchar에만 해당)
    public bool IsNullable { get; set; } = true;     // Null 허용 여부
}

public class StoredProcedureRawdata
{
    public required string ProcedureName { get; set; }
    public string? Caller { get; set; }
    public int? ParameterId { get; set; }
    public string? ParameterName { get; set; }
    public string? TypeName { get; set; }
    public int? MaxLength { get; set; }
    public bool? IsNullable { get; set; }
}