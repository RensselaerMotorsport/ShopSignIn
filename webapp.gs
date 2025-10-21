var SPREADSHEET_ID = "1NcW4DqQr9W4dRV4CPHQSa4G9ISCfxIq2rJ4OiikBKzg";
var FORM_ID = "1qHjkJTgvlwGOtaP2H0A_xrqtofIQDJyeQt1tFo6atCs";
var idColumn = 1;
var timeColumn = 2;

function doGet(e) {
  if (!e || !e.parameter || !e.parameter.sts) {
    return ContentService.createTextOutput("Missing parameters")
      .setMimeType(ContentService.MimeType.TEXT);
  }

  var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  var logSheet = ss.getSheetByName("Attendance Log");
  var uidSheet = ss.getSheetByName("UID");
  var memberSheet = ss.getSheetByName("Member");

  var sts = e.parameter.sts;
  Logger.log("Received request, sts=" + sts + " params=" + JSON.stringify(e.parameter));

  if (sts == "writelog") {
    var name = e.parameter.name || "";
    var inout = e.parameter.inout || "";
    var date = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd");

    var inTime = "";
    var outTime = "";

    if (inout === "IN") {
      inTime = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "HH:mm:ss");
    } else if (inout.includes("->")) {
      var parts = inout.split("->");
      inTime = parts[0].trim();
      outTime = parts[1].trim();
    }

    logSheet.appendRow([name, inTime, outTime, date]);

  } else if (sts == "writeuid") {
    var uid = e.parameter.uid || "";
    var time = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "MM/dd/yyyy|h:mm:ssa");
    var data = uidSheet.getDataRange().getValues();
    var found = false;
    for (var i = 0; i < data.length; i++) {
      if (data[i][0] == uid) {
        uidSheet.getRange(i + 1, 2).setValue(time);
        found = true;
        break;
      }
    }
    if (!found) {
      uidSheet.appendRow([uid, time]);
      spreadSheetGetter(); 
    }

  } else if (sts == "addmember") {
    var uid = e.parameter.uid || "";
    var name = e.parameter.name || "";
    var rin = e.parameter.rin || "";
    memberSheet.appendRow([uid, name, rin]);

  } else if (sts == "removeuid") {
    var uid = e.parameter.uid || "";
    var data = uidSheet.getDataRange().getValues();
    for (var i = data.length - 1; i >= 0; i--) {
      if (data[i][0] == uid) {
        uidSheet.deleteRow(i + 1);
      }
    }

  } else if (sts == "getmembers") {
    var data = memberSheet.getDataRange().getValues();
    var result = [];
    for (var i = 0; i < data.length; i++) {
      result.push({
        uid: data[i][0],
        name: data[i][1],
        rin: data[i][2]
      });
    }
    return ContentService.createTextOutput(JSON.stringify(result))
      .setMimeType(ContentService.MimeType.JSON);
  }

  return ContentService.createTextOutput("OK")
    .setMimeType(ContentService.MimeType.TEXT);
}

// Updates the form dropdown with UID list
function spreadSheetGetter() {
  var sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName("UID");
  var lr = sheet.getLastRow();
  if (lr < 2) return;

  var values = sheet.getRange(2, idColumn, lr - 1, 2).getValues();
  var docIds = values.map(function(row) {
    if (row[0] && row[1]) {
      return row[0] + " - " + row[1];
    } else if (row[0]) {
      return row[0];
    } else {
      return null;
    }
  }).filter(String);

  fillFormData(docIds);
}

// Updates the form list item
function fillFormData(docIds) {
  var form = FormApp.openById(FORM_ID);
  var item = form.getItems(FormApp.ItemType.LIST)[0].asListItem();
  item.setChoices(docIds.map(id => item.createChoice(id)));
}

// Trigger: Sheet change
function onSheetChange(e) {
  spreadSheetGetter();
}

// Trigger: Form submission
function onFormSubmit(e) {
  try {
    var ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    var formSheet = ss.getSheetByName("Form Responses 2");
    var uidSheet = ss.getSheetByName("UID");
    var memberSheet = ss.getSheetByName("Member");

    var lastRow = formSheet.getLastRow();
    var rowValues = formSheet.getRange(lastRow, 1, 1, formSheet.getLastColumn()).getValues()[0];

    var uid = parseUID(rowValues[1]);
    var name = rowValues[2];
    var nickname = rowValues[3];
    var rin = rowValues[4];

    if (nickname && nickname.trim() !== "") {
      name = nickname.trim();
    }

    memberSheet.appendRow([uid, name, rin]);
    removeUIDfromSheet(uidSheet, uid);
    spreadSheetGetter(); // refresh dropdown after removal
    Logger.log("Form submitted. Row values: " + JSON.stringify(rowValues));
  } catch (err) {
    Logger.log("Form Submit Error: " + err);
  }
}

// Helper: Parse UID from form selection
function parseUID(selection) {
  if (!selection) return "";
  return selection.split("-")[0].trim();
}

// Helper: Remove UID from sheet
function removeUIDfromSheet(uidSheet, uid) {
  var data = uidSheet.getDataRange().getValues();
  for (var i = data.length - 1; i >= 0; i--) {
    if (data[i][0] == uid) {
      uidSheet.deleteRow(i + 1);
    }
  }
}