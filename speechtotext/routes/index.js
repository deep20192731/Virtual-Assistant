var express = require('express');
var router = express.Router();
var multer = require('multer');
var fs=require('fs');
var upload = multer({ dest: './files/' });
var request = require('request');
function callffmpeg(fil,type,callback){            
//    var new_name='ip_'+new Date().getTime()+'.flac';
//    fs.rename('./files/'+fil,'./files/'+new_name);
//    fil=new_name
    var ffmpeg = require('ffmpeg');
    try {
        var process = new ffmpeg('./files/'+fil);
        process.then(function (video) {
            video
            .setAudioCodec('flac')
            .setAudioChannels(1)
            .setVideoStartTime(0)
            .setVideoDuration(60)
            .save('./files/op_'+new Date().getTime()+'.flac', function (error, file) {
                if (!error){
                    fs.unlink('./files/'+fil, (err) => {
                        if (err) callback(new Error(err));
                    });
                   console.log(file) 
                   syncRecognize (file,type,callback)
                }else{
                    console.log(error)
                    callback(new Error(error))
                }
            });
        },function (err) {
            console.log('Error: ' + err);
            callback(new Error(err))
        });
    }catch (e) {
        console.log(e.code);
        console.log(e.msg);
        callback(new Error(e.msg))
    }
}
function syncRecognize (filename,type,callback) {

  const config = {
      projectId: 'speech-test',
      keyFilename: './speech-test-5b2c2cb2f139.json'
  };
  const speech =require('@google-cloud/speech')(config);
  const languageCode = 'en-US';

  const request = {
    languageCode: languageCode
  };

  speech.recognize(filename, request)
    .then((results) => {
      const transcription = results[0];
      fs.unlink(filename, (err) => {
        if (err) callback(new Error(err));
      
});
      console.log(`Transcription: ${transcription}`);
      if(type=='speech'){
        get_tone(transcription,callback);    
      }else{
          botrequest(transcription,callback);
      }   
  })
    .catch((err) => {
      callback(new Error(err))
      //console.error('ERROR:', err);
    });
  
}

function botrequest(transcription,callback){
    request({
            url: "https://nbk6ta8rdb.execute-api.us-west-2.amazonaws.com/prod/botResponse", 
            method:"POST",
            json:{text: transcription,context:{}}
//            json:true,
//            headers:{
//                "content-type": "application/json",
//            },
//            body: JSON.stringify({text: transcription,context:{}})
        },
        function(error, response, body){
            if(error){
                callback(new Error(error));
            }else{
                result={
                    transcript:transcription,
                    response:body
                }
                callback(null,result);
            } 
    });
}

function get_tone(input,callback){
    var NaturalLanguageUnderstandingV1 = require('watson-developer-cloud/natural-language-understanding/v1.js');
    var natural_language_understanding = new NaturalLanguageUnderstandingV1({
      username: '32e781bd-4e1b-4938-902e-48ba06e4139d',
      password: 'Kjk57yEkJ7YM',
      version_date: NaturalLanguageUnderstandingV1.VERSION_DATE_2017_02_27
    });

    var parameters = {
      'text': input,
      'features': {
        'entities': {
          'limit': 5
        },
        'keywords': {
          'limit': 5
        },
        'sentiment':{

        }
      }
    }

    natural_language_understanding.analyze(parameters, function(err, response) {
      if (err){
        console.log(err);
        callback(new Error(err));
      }
      else{
          var keywords=get_keywords(response['keywords']);
          var entities=get_entities(response['entities'])
          var result={
              transcript:input,
              sentiment:response['sentiment']['document']['label'],
              keywords:keywords,
              entities:entities
          }
          console.log(response)
          console.log(JSON.stringify(response, null, 2));
          callback(null,result)
            
      }
        
    });
}
function get_keywords(data){
    var keywords=[];
    for(i=0;i<data.length;i++){
        keywords.push(data[i]['text']);
    }
    
return keywords;
}

function get_entities(data){
    var entities=[];
    for(i=0;i<data.length;i++){
        entities.push(data[i]['text']);
    }
    
return entities;
}
function asyncOperation(file_det,type,callback){    
//    fs.rename('./files/'+file_det['filename'],'./files/'+file_det['originalname'],function(err){
//        if (err)
//        callback(new Error(err));
//    });
    callffmpeg(file_det['filename'],type,callback);
}



/* GET home page. */
router.get('/', function(req, res, next) {
  res.render('index', { title: 'Express' });
});

router.post('/bot', upload.any(),function(req,res,next){
    var file_det=req.files[0];
    asyncOperation (file_det,'bot',function ( err, response ) {
        res.send(response);
    });
    
});

router.post('/speech_analysis', upload.any(),function(req,res,next){
    var file_det=req.files[0];
    asyncOperation (file_det,'speech',function ( err, response ) {
        res.send(response);
    });
    
});
module.exports = router;
