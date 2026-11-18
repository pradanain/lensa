export function passwordRules(value:string){
  return [
    {label:'Minimal 8 karakter',valid:value.length>=8&&value.length<=256},
    {label:'Satu huruf besar (A–Z)',valid:/[A-Z]/.test(value)},
    {label:'Satu angka (0–9)',valid:/[0-9]/.test(value)},
    {label:'Satu simbol, misalnya ! @ #',valid:/[^\p{L}\p{N}\s]/u.test(value)},
  ]
}
